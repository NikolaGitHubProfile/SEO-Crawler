import requests
from selectolax.parser import HTMLParser
from urllib.parse import urljoin, urlparse
import csv
from concurrent.futures import ThreadPoolExecutor
import re
import xml.etree.ElementTree as ET
import time
from collections import Counter
import unicodedata
from nltk import ngrams

# Croatian stop words (common words that don't carry much meaning)
CROATIAN_STOP_WORDS = set([
    'i', 'u', 'je', 'da', 'na', 'se', 'za', 'ne', 'to', 'su', 'koje', 'što',
    'ili', 'iz', 'bi', 'kao', 'od', 'te', 'do', 'pri', 'ni', 'kako', 'jer',
    'samo', 'oko', 'već', 'tako', 'sve', 'kada', 'još', 'po', 'čak', 'šta',
    'iako', 'dok', 'tek', 'gdje', 'kao', 'god', 'koja', 'koje', 'koji', 'kroz',
    'acc'
])


class SEOCrawler:
    def __init__(self, start_url, max_pages=100):
        self.start_url = start_url
        self.max_pages = max_pages
        self.visited_urls = set()
        self.to_visit = [start_url]
        self.domain = urlparse(start_url).netloc
        self.seo_data = []
        self.sitemap_urls = set()
        self.robots_txt_content = ""
        self.response_codes = {}


    def crawl(self):
        self.check_robots_txt()
        self.check_sitemap()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            while self.to_visit and (self.max_pages is None or len(self.visited_urls) < self.max_pages):
                futures = []
                for _ in range(min(5, len(self.to_visit))):
                    if self.to_visit and (self.max_pages is None or len(self.visited_urls) < self.max_pages):
                        url = self.to_visit.pop(0)
                        if url not in self.visited_urls:
                            self.visited_urls.add(url)
                            futures.append(executor.submit(self.process_page, url))
                
                for future in futures:
                    future.result()
                print(f"Processed {len(self.visited_urls)} pages. Queue: {len(self.to_visit)} pages.")

    def check_robots_txt(self):
        robots_url = urljoin(self.start_url, "/robots.txt")
        try:
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                self.robots_txt_content = response.text
            else:
                print(f"No robots.txt found at {robots_url}")
        except requests.RequestException as e:
            print(f"Error fetching robots.txt: {str(e)}")

    def check_sitemap(self):
        sitemap_url = urljoin(self.start_url, "/sitemap.xml")
        try:
            response = requests.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                self.parse_sitemap(response.content)
            else:
                print(f"No sitemap found at {sitemap_url}")
        except requests.RequestException as e:
            print(f"Error fetching sitemap: {str(e)}")

    def parse_sitemap(self, content):
        try:
            root = ET.fromstring(content)
            namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            # Check if it's a sitemap index
            sitemaps = root.findall('.//sm:sitemap/sm:loc', namespace)
            if sitemaps:
                for sitemap in sitemaps:
                    sitemap_url = sitemap.text
                    self.fetch_and_parse_sitemap(sitemap_url)
            else:
                # It's a regular sitemap
                self.extract_urls_from_sitemap(root, namespace)
        except ET.ParseError as e:
            print(f"Error parsing sitemap XML: {str(e)}")

    def fetch_and_parse_sitemap(self, url):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                self.extract_urls_from_sitemap(root, namespace)
            else:
                print(f"Failed to fetch sitemap at {url}")
        except requests.RequestException as e:
            print(f"Error fetching sitemap {url}: {str(e)}")
        except ET.ParseError as e:
            print(f"Error parsing sitemap XML from {url}: {str(e)}")

    def extract_urls_from_sitemap(self, root, namespace):
        for url in root.findall('.//sm:url/sm:loc', namespace):
            self.sitemap_urls.add(url.text)

    def process_page(self, url):
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            load_time = time.time() - start_time
            
            # Store the response code
            self.response_codes[url] = response.status_code

            if response.status_code == 200:
                parser = HTMLParser(response.text)
                self.extract_seo_components(url, parser, load_time, response.headers)
                self.find_links(url, parser)
            else:
                print(f"Received status code {response.status_code} for URL: {url}")
        except requests.RequestException as e:
            print(f"Request failed for {url}: {str(e)}")
            self.response_codes[url] = getattr(e.response, 'status_code', None) or 'Connection Error'
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")

    def extract_seo_components(self, url, parser, load_time, headers):
        title_node = parser.css_first('title')
        title = title_node.text() if title_node else ""

        meta_description_node = parser.css_first('meta[name="description"]')
        meta_description = meta_description_node.attributes.get('content', '') if meta_description_node else ""

        h1_tags = parser.css('h1')
        h1_contents = [h1.text() for h1 in h1_tags]

        h2_tags = parser.css('h2')
        h2_contents = [h2.text() for h2 in h2_tags]

        keywords = self.extract_keywords(parser)
        images = self.extract_images(parser)
        links = self.find_links(url, parser)
        content_length = len(parser.body.text())
        
        self.seo_data.append({
            'url': url,
            'title': title,
            'meta_description': meta_description,
            'h1_tags': h1_contents,
            'h2_tags': h2_contents,
            'keywords': keywords,
            'images': images,
            'internal_links': len(links['internal']),
            'external_links': len(links['external']),
            'load_time': load_time,
            'content_length': content_length,
            'is_https': url.startswith('https'),
            'server': headers.get('Server', ''),
            'content_type': headers.get('Content-Type', '')
        })

    def extract_keywords(self, parser):
        keywords = []

        # Extract product name
        product_name = parser.css_first('h1, .name, .product-title, .product-name ')
        if product_name:
            keywords.extend(self.tokenize(product_name.text()))

        # Extract product description
        description_selectors = [
            '.product-description', '[itemprop="description"]', 
            '.description', '#product-description', '.product-details', '.tab-details',
            '.product__listing--description'
        ]
        for selector in description_selectors:
            description = parser.css_first(selector)
            if description:
                keywords.extend(self.tokenize(description.text()))
                break

        # Extract product categories
        category_selectors = [
            '.breadcrumb a', '.categories a', '.product-category', 
            'nav[aria-label="breadcrumb"] a'
        ]
        for selector in category_selectors:
            categories = parser.css(selector)
            for category in categories:
                keywords.extend(self.tokenize(category.text()))

        # Extract product specifications
        spec_selectors = [
            '.product-specifications li', '.product-attrs li', 
            '.product-features li', '.specs-table tr', '.tabbody specscont'
        ]
        for selector in spec_selectors:
            specs = parser.css(selector)
            for spec in specs:
                keywords.extend(self.tokenize(spec.text()))

        # Extract customer reviews
        review_selectors = [
            '.customer-reviews .review-text', '.product-reviews .review-content',
            '#reviews .review-body', '.tabbody.reviewcont'
        ]
        for selector in review_selectors:
            reviews = parser.css(selector)
            for review in reviews:
                keywords.extend(self.tokenize(review.text()))

        # Extract meta keywords if available
        meta_keywords = parser.css_first('meta[name="keywords"]')
        if meta_keywords:
            keywords.extend(self.tokenize(meta_keywords.attributes.get('content', '')))

        # Group similar keywords
        grouped_keywords = self.group_similar_keywords(keywords)

        # Filter and count keywords
        keyword_counts = Counter(grouped_keywords)
        return keyword_counts.most_common(20)  # Top 20 keywords

    def tokenize(self, text):
        # Normalize unicode characters
        text = unicodedata.normalize('NFKC', text.lower())

        # Tokenize
        words = re.findall(r'\b\w+\b', text)

        # Filter words
        filtered_words = [word for word in words 
                          if word not in CROATIAN_STOP_WORDS 
                          and len(word) > 2
                          and not word.isdigit()]

        # Generate n-grams
        bigrams = [' '.join(ng) for ng in ngrams(filtered_words, 2)]
        trigrams = [' '.join(ng) for ng in ngrams(filtered_words, 3)]

        return filtered_words + bigrams + trigrams

    def group_similar_keywords(self, keywords):
        grouped = []
        for word in keywords:
            # Check for plural forms (very simplified)
            if word.endswith('i') and word[:-1] in keywords:
                grouped.append(word[:-1])
            elif word + 'i' in keywords:
                grouped.append(word)
            # Check for adjective forms (very simplified)
            elif word.endswith('ski') and word[:-3] in keywords:
                grouped.append(word[:-3])
            elif word + 'ski' in keywords:
                grouped.append(word)
            else:
                grouped.append(word)
        return grouped

    def extract_images(self, parser):
        images = []
        for img in parser.css('img'):
            alt = img.attributes.get('alt', '')
            src = img.attributes.get('src', '')
            images.append({'src': src, 'alt': alt})
        return images

    def find_links(self, base_url, parser):
        internal_links = []
        external_links = []
        for a in parser.css('a'):
            href = a.attributes.get('href')
            if href:
                try:
                    url = urljoin(base_url, href)
                    parsed_url = urlparse(url)
                    if parsed_url.netloc == self.domain:
                        internal_links.append(url)
                        if url not in self.visited_urls:
                            self.to_visit.append(url)
                    elif parsed_url.scheme in ('http', 'https'):
                        external_links.append(url)
                except ValueError as e:
                    print(f"Error parsing URL {href}: {str(e)}")
        return {'internal': internal_links, 'external': external_links}

    def evaluate_seo(self):
        for page in self.seo_data:
            page['issues'] = []

            # Evaluate response code
            response_code = self.response_codes.get(page['url'])
            if response_code != 200:
                page['issues'].append(f"Non-200 response code: {response_code}")
            
            # Title evaluation
            if not page['title']:
                page['issues'].append("Missing title tag")
            elif len(page['title']) < 30 or len(page['title']) > 60:
                page['issues'].append("Title length should be between 30-60 characters")
            elif not any(keyword.lower() in page['title'].lower() for keyword, _ in page['keywords'][:3]):
                page['issues'].append("Title doesn't contain any of the top 3 keywords")
            
            # Meta description evaluation
            if not page['meta_description']:
                page['issues'].append("Missing meta description")
            elif len(page['meta_description']) < 120 or len(page['meta_description']) > 160:
                page['issues'].append("Meta description should be between 120-160 characters")
            elif not any(keyword.lower() in page['meta_description'].lower() for keyword, _ in page['keywords'][:3]):
                page['issues'].append("Meta description doesn't contain any of the top 3 keywords")

            # Evaluate redirects
            if str(response_code).startswith('3'):
                page['issues'].append(f"Page is redirecting (status code {response_code})")

            # Evaluate client errors
            if str(response_code).startswith('4'):
                page['issues'].append(f"Client error (status code {response_code})")

            # Evaluate server errors
            if str(response_code).startswith('5'):
                page['issues'].append(f"Server error (status code {response_code})")
            
            # H1 tag evaluation
            if not page['h1_tags']:
                page['issues'].append("Missing H1 tag")
            elif len(page['h1_tags']) > 1:
                page['issues'].append(f"Multiple H1 tags found ({len(page['h1_tags'])}). Consider using only one H1 tag per page.")
            
            for i, h1_content in enumerate(page['h1_tags']):
                if len(h1_content) < 20 or len(h1_content) > 70:
                    page['issues'].append(f"H1 tag {i+1} length ({len(h1_content)} characters) is not optimal. Aim for 20-70 characters.")
                if not any(keyword.lower() in h1_content.lower() for keyword, _ in page['keywords'][:3]):
                    page['issues'].append(f"H1 tag {i+1} doesn't contain any of the top 3 keywords.")
            
            # Page load time evaluation
            if page['load_time'] > 3:
                page['issues'].append(f"Slow page load time: {page['load_time']:.2f} seconds")

            # Image evaluation
            if not page['images']:
                page['issues'].append("No images found on the page")
            else:
                missing_alt = sum(1 for img in page['images'] if not img['alt'])
                if missing_alt:
                    page['issues'].append(f"{missing_alt} images missing alt text")

            # Internal linking evaluation
            if not page['internal_links']:
                page['issues'].append("No internal links found")
            elif page['internal_links'] < 3:
                page['issues'].append(f"Only {page['internal_links']} internal links found. Consider adding more.")

            # Sitemap evaluation
            if page['url'] not in self.sitemap_urls:
                page['issues'].append("URL not found in sitemap")

            # URL structure evaluation
            if not self.is_url_seo_friendly(page['url']):
                page['issues'].append("URL is not SEO-friendly")

            # Content length evaluation
            if page['content_length'] < 300:
                page['issues'].append("Content length is too short. Aim for at least 300 words.")

            # HTTPS evaluation
            if not page['is_https']:
                page['issues'].append("Page is not served over HTTPS")

            # Keyword evaluation
            if not page['keywords']:
                page['issues'].append("No prominent keywords found")
            else:
                page['issues'].append(f"Top keywords: {', '.join([word for word, _ in page['keywords'][:5]])}")


    def is_url_seo_friendly(self, url):
        parsed = urlparse(url)
        path = parsed.path
        return all([
            '-' in path,  # Contains hyphens
            not re.search(r'\d{4,}', path),  # Doesn't contain long numbers
            not re.search(r'[A-Z]', path),  # Doesn't contain uppercase letters
            not re.search(r'[?&]', url)  # Doesn't contain query parameters
        ])

    def save_results(self):
        with open('seo_analysis.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['url', 'response_code', 'title', 'meta_description', 'h1_tags', 'h2_tags', 'load_time', 'keywords', 'internal_links', 'external_links', 'issues'])
            writer.writeheader()
            for page in self.seo_data:
                writer.writerow({
                    'url': page['url'],
                    'response_code': self.response_codes.get(page['url'], 'Unknown'),
                    'title': page['title'],
                    'meta_description': page['meta_description'],
                    'h1_tags': ' | '.join(page['h1_tags']),
                    'h2_tags': ' | '.join(page['h2_tags']),
                    'load_time': f"{page['load_time']:.2f}",
                    'keywords': ', '.join([f"{word}({count})" for word, count in page['keywords']]),
                    'internal_links': page['internal_links'],
                    'external_links': page['external_links'],
                    'issues': ', '.join(page['issues'])
                })

        print("SEO analysis complete. Results saved in seo_analysis.csv")
        
        # Print a summary of response codes
        print("\nResponse Code Summary:")
        code_counter = Counter(self.response_codes.values())
        for code, count in code_counter.items():
            print(f"Status {code}: {count} pages")

if __name__ == "__main__":
    start_url = "https://www.ekupi.hr"  # Replace with the website you want to crawl
    max_pages = 100
    crawler = SEOCrawler(start_url, max_pages)
    crawler.crawl()
    crawler.evaluate_seo()
    crawler.save_results()
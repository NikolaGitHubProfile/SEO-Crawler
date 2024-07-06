# SEO Analysis Script

This Python script enables simple SEO analysis of a website by crawling its pages and evaluating various SEO components. The tool is designed to help assess and optimize web pages for search engine visibility and user experience.

## Features

- **Crawling:** Initiates crawling from a specified starting URL (`start_url`) and visits subsequent pages up to a specified maximum (`max_pages`).
  
- **Concurrency:** Utilizes `ThreadPoolExecutor` for concurrent page fetching to optimize performance and speed up the crawling process.

- **Robots.txt and Sitemap Handling:** Checks for and retrieves `robots.txt` and `sitemap.xml` files from the website to ensure compliance and efficient crawling.

- **SEO Components Extraction:** Extracts essential SEO elements from each page, including:
  - Title tags
  - Meta descriptions
  - Headers (`h1`, `h2`)
  - Keywords
  - Images and their alt text
  - Internal and external links
  
- **SEO Evaluation:** Evaluates each page against predefined SEO criteria, such as:
  - Response codes (e.g., 200, 404)
  - Length and presence of title and meta description
  - Keyword presence and prominence
  - Page load time
  - HTTPS usage
  - Internal linking structure
  - Sitemap inclusion
  - URL structure
  
- **Results Storage:** Saves the evaluated SEO data into a CSV file (`seo_analysis.csv`) for detailed analysis and reporting. The CSV file includes:
  - URL
  - Response code
  - Title
  - Meta description
  - H1 and H2 tags
  - Load time
  - Keywords and their frequencies
  - Internal and external links
  - Identified SEO issues
  
- **Error Handling:** Includes robust error handling to manage exceptions during crawling, parsing, and evaluation processes, ensuring reliability and continuity of the analysis.

## Usage

1. **Setup:** Replace `start_url` in the script with the URL of the website you want to analyze. Adjust `max_pages` as needed to control the depth of crawling.

2. **Execution:** Run the script in a Python 3.x environment. Ensure that required Python packages (`requests`, `selectolax`, `nltk`, `xml.etree.ElementTree`) are installed.

3. **Results:** After completion, review the `seo_analysis.csv` file generated in the current directory for a detailed SEO audit report and summary of response codes encountered.

## Customization

- **Criteria:** Customize the script to add or modify SEO evaluation criteria based on specific SEO requirements or site characteristics.
  
- **Extensions:** Extend functionality by incorporating additional SEO factors or integrating with external tools for deeper analysis or visualization.

## Requirements

- Python 3.x
- Required Python packages listed in `requirements.txt` or installed via `pip`.

## Notes

- Ensure adequate network connectivity and permissions for crawling the website.
- For large websites or specific SEO challenges, consider adjusting concurrency settings or integrating with cloud services for scalable performance.

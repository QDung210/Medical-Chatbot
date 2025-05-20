import aiohttp
import asyncio
from bs4 import BeautifulSoup
import os
import time
import json
import re
from urllib.parse import urljoin
from datetime import datetime, timedelta
import functools
import random 

def timing_decorator(func):
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Function {func.__name__} took {elapsed_time:.2f} seconds ({str(timedelta(seconds=int(elapsed_time)))})")
        return result
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Function {func.__name__} took {elapsed_time:.2f} seconds ({str(timedelta(seconds=int(elapsed_time)))})")
        return result
    
    # Return appropriate wrapper based on whether func is async or not
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper

class VinmecScraper:
    def __init__(self, base_url, output_file="all_articles.json", max_concurrency=5):
        self.base_url = base_url
        self.output_file = output_file
        self.articles = []
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.106 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.106 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.3; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/123.0.2420.65",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.106 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.106 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        ]
        self.headers = {'User-Agent': random.choice(self.user_agents)}
        self.semaphore = asyncio.Semaphore(max_concurrency)  # Control concurrency
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    
    async def get_page(self, session, url):
        try:
            async with self.semaphore:  # Limit concurrent requests
                async with session.get(url, headers=self.headers, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        print(f"Error fetching {url}: Status {response.status}")
                        return None
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_article_links(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        article_links = []
        for section in soup.find_all('div', class_='flex list_four_new mini-post'):
            for link in section.find_all('a', href=True):
                url = urljoin(self.base_url, link['href'])
                if "/bai-viet/" in url and url not in article_links:
                    article_links.append(url)
        return article_links
    
    def extract_article_content(self, html, url):
        soup = BeautifulSoup(html, 'html.parser')
        title_element = soup.find('h1', class_='single-title single-title-line')
        if not title_element:
            return None
        
        title = title_element.text.strip()
        content_element = soup.find('div', id='main-article', class_='entry')
        if not content_element:
            return None
            
        # Remove unwanted elements
        for tag in content_element.find_all(['script', 'style', 'iframe', 'section']):
            tag.decompose()
        
        # Extract text from paragraphs and headings
        text = ""
        for tag in content_element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li']):
            text += "\n" + tag.get_text(strip=True)
        
        # Clean up text
        text = text.strip()
        text = re.sub(r'\n+', '\n', text)
        
        # Remove booking text
        text = re.sub(r'Để đặt lịch khám tại viện,.*?ứng dụng\.', '', text)
        
        return {'url': url, 'title': title, 'content': text}
    
    async def scrape_article(self, session, link):
        html = await self.get_page(session, link)
        if html:
            article = self.extract_article_content(html, link)
            if article:
                print(f"Scraped: {article['title']}")
                return article
        return None
    
    @timing_decorator
    async def scrape(self, start_page=0):
        async with aiohttp.ClientSession() as session:
            page_num = start_page
            keep_scraping = True
            
            while keep_scraping:
                page_url = self.base_url.replace('page_0', f'page_{page_num}')
                print(f"Scraping page {page_num}: {page_url}")
                
                html = await self.get_page(session, page_url)
                if not html:
                    print(f"Could not fetch page {page_num}. Stopping.")
                    break
                    
                links = self.extract_article_links(html)
                if not links:
                    print(f"No articles found on page {page_num}. Stopping.")
                    break
                
                # Create and gather tasks for all articles on the page
                tasks = [self.scrape_article(session, link) for link in links]
                results = await asyncio.gather(*tasks)
                
                # Filter out None results
                articles = [article for article in results if article is not None]
                self.articles.extend(articles)
                
                print(f"Page {page_num}: Found {len(articles)} articles")
                
                # Brief delay between pages to be nice to the server
                await asyncio.sleep(1)
                
                # Move to next page
                page_num += 1
        
        return self.articles

async def main():
    base_urls = ["https://www.vinmec.com/vie/tim-mach/page_0",
                "https://www.vinmec.com/vie/thong-tin-suc-khoe/page_0",
                "https://www.vinmec.com/vie/trung-tam-cham-soc-suc-khoe-tinh-than/page_0",
                "https://www.vinmec.com/vie/trung-tam-mat/page_0"
                ]
    output_path = r"C:\Users\Admin\Documents\vinmec\second.json"
    
    start_time = time.time()
    
    # Collect all articles from all URLs
    all_articles = []
    
    for url in base_urls:
        scraper = VinmecScraper(url, output_path, max_concurrency=5)
        articles = await scraper.scrape(start_page=0)
        all_articles.extend(articles)
        print(f"Collected {len(articles)} articles from {url}")
    
    # Save all articles to JSON file directly without metadata
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    
    end_time = time.time()
    total_time = end_time - start_time
    print(f"Saved {len(all_articles)} articles to {output_path}")
    print(f"Total execution time: {total_time:.2f} seconds ({str(timedelta(seconds=int(total_time)))})")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 
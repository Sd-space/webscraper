from flask import Flask, render_template, request, redirect, url_for, send_from_directory, send_file
import os
import csv
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random
from fake_useragent import UserAgent
from requests.exceptions import RequestException, Timeout, ConnectionError

app = Flask(__name__)

# Configuration for file upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Check if the uploaded file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Create a UserAgent object for User-Agent rotation
user_agent = UserAgent()

# Your Amazon scraping function
def scrape_amazon(url, csv_filename, num_pages):
    products = []
    try:
        for page in range(1, num_pages + 1):
            current_url = f"{url}&page={page}"
            headers = {'User-Agent': user_agent.random}
            time.sleep(random.uniform(1, 5))
            r = requests.get(current_url, headers=headers, timeout=10)
            r.raise_for_status()

            soup = BeautifulSoup(r.content, 'html.parser')
            for product in soup.find_all('div', {'data-asin': True}):
                title_element = product.find('span', {'class': 'a-size-medium'})
                title = title_element.text.strip() if title_element else 'N/A'

                price_element = product.find('span', {'class': 'a-offscreen'})
                price = price_element.text.strip() if price_element else 'N/A'

                rating_element = product.find('span', {'class': 'a-icon-alt'})
                rating = rating_element.text.strip() if rating_element else 'N/A'

                image_element = product.find('img', {'src': True})
                image_url = image_element['src'] if image_element else 'N/A'

                if 'N/A' not in (title, price, rating):
                    products.append({'Title': title, 'Price': price, 'Rating': rating, 'Image': image_url})
        return products
    except (RequestException, Timeout, ConnectionError) as e:
        return str(e)

# Your Flipkart scraping function remains unchanged
def scrape_flipkart(url, num_pages):
    try:
        Product_name = []
        Prices = []
        Reviews = []
        Images = []

        for page in range(1, num_pages + 1):
            page_url = f"{url}&page={page}"
            r = requests.get(page_url, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")

            products = soup.find_all("div", class_="_2kHMtA")

            if not products:
                break

            for product in products:
                try:
                    name = product.find("div", class_="_4rR01T").text.strip()
                    Product_name.append(name)
                except AttributeError:
                    Product_name.append('Not available')

                try:
                    price = product.find("div", class_="_30jeq3").text.strip()
                    Prices.append(price)
                except AttributeError:
                    Prices.append('Not available')
                
                try:
                    review = product.find("div", class_="_3LWZlK").text.strip()
                    Reviews.append(review)
                except AttributeError:
                    Reviews.append('Not available')

                try:
                    image = product.find("img")['src']
                    Images.append(image)
                except AttributeError:
                    Images.append('N/A')

        scraped_data = {"Product Name": Product_name, "Prices": Prices, "Reviews": Reviews, "Images": Images}
        return scraped_data
    except (RequestException, Timeout, ConnectionError) as e:
        return str(e)

# Route for the welcome page
@app.route('/')
def welcome():
    return render_template('welcome.html', css_file=url_for('static', filename='style.css'))

# Route for Amazon scraping page
@app.route('/amazon')
def amazon():
    return render_template('amazon.html', css_file=url_for('static', filename='style.css'))

# Route for Flipkart scraping page
@app.route('/flipkart')
def flipkart():
    return render_template('flipkart.html', css_file=url_for('static', filename='style.css'))

# Route to handle Amazon scraping
@app.route('/scrape_amazon', methods=['POST'])
def scrape_amazon_route():
    url = request.form['url']
    csv_filename = request.form['csv_filename']
    num_pages = int(request.form['num_pages'])

    products = scrape_amazon(url, csv_filename, num_pages)

    if isinstance(products, list):
        csv_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{csv_filename}.csv")
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['Title', 'Price', 'Rating', 'Image']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)

        # Pass a parameter indicating success to the template
        return redirect(url_for('download_file', filename=f"{csv_filename}.csv", success=True))
    else:
        return products

# Route to handle Flipkart scraping
@app.route('/scrape_flipkart', methods=['POST'])
def scrape_flipkart_route():
    url = request.form['url']
    num_pages = int(request.form['num_pages'])

    scraped_data = scrape_flipkart(url, num_pages)

    if isinstance(scraped_data, dict):
        csv_filename = request.form['csv_filename']
        csv_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{csv_filename}.csv")
        df = pd.DataFrame(scraped_data)
        df.to_csv(csv_file_path, index=False)

        # Pass a parameter indicating success to the template
        return redirect(url_for('download_file', filename=f"{csv_filename}.csv", success=True))
    else:
        return "Error: Failed to scrape Flipkart data."

# Route to download CSV file
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    success = request.args.get('success', default=False, type=bool)
    if success:
        # Render the template with a success message
        return render_template('download.html', filename=filename)
    else:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Route to download Excel file
@app.route('/download_excel/<filename>', methods=['GET'])
def download_excel(filename):
    csv_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    excel_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace('.csv', '.xlsx'))
    df = pd.read_csv(csv_file_path)
    df.to_excel(excel_file_path, index=False)
    return send_file(excel_file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)

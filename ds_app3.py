import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
import re
from pymongo import MongoClient
from scipy.stats import f_oneway


def scrape_books():
    base_url = 'https://books.toscrape.com/catalogue/page-{}.html'
    first_page = 'https://books.toscrape.com/'

    book_titles, book_prices, book_ratings = [], [], []

    for page_num in range(1, 51):
        url = first_page if page_num == 1 else base_url.format(page_num)
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        books = soup.find_all('article', class_='product_pod')

        for book in books:
            title = book.find('h3').find('a')['title']
            price = book.find('p', class_='price_color').text
            rating = book.find('p', class_='star-rating')['class'][1]

            book_titles.append(title)
            book_prices.append(price)
            book_ratings.append(rating)

    data = {
        'Title': book_titles,
        'Price': book_prices,
        'Rating': book_ratings
    }
    return pd.DataFrame(data)

def clean_data(df):
    df['Price'] = df['Price'].apply(lambda x: float(re.sub(r'[^\d.]', '', x)))

    def extract_rating(rating_word):
        word_to_num = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}
        match = re.search(r'(One|Two|Three|Four|Five)', rating_word)
        return word_to_num[match.group()] if match else None

    df['Rating'] = df['Rating'].apply(extract_rating)
    df = df[(df['Price'] > 0) & (df['Price'] < 100)].drop_duplicates().dropna()
    return df

def save_to_mongodb(df):
    uri = "mongodb+srv://duck:oncrack@cluster0.nq1oxaw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(uri)
    db = client['mydatabase']
    collection = db['mycollection']
    collection.delete_many({})
    documents = df.to_dict('records')
    collection.insert_many(documents)
    return collection

def set_background_color(color_hex):
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {color_hex};
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Set background color
set_background_color("#FAF9F6")  # Very light cream

st.title('📚 Book Scraper and Analyzer')
if 'df' not in st.session_state:
    st.session_state.df = None

if st.button('Scrape and Analyze Books Data'):
    with st.spinner('Scraping books data from website...'):
        df = scrape_books()
        df = clean_data(df)
        df.to_csv('books_data.csv', index=False)
        st.session_state.df = df  # <-- Save it to session_state
        st.success("Data scraped, cleaned, and saved locally!")
df = st.session_state.df

if st.button('📋 Sample of Scraped Data'):
    if df is not None:
        st.dataframe(df.head(10))
    else:
        st.warning('Please scrape the data first.')

if st.button('📊 ANOVA & Basic Statistics'):
    if df is not None:
        st.subheader('📊 ANOVA: Does Book Price Vary by Rating?')

        # Group prices by rating
        prices_by_rating = [df[df['Rating'] == rating]['Price'] for rating in sorted(df['Rating'].unique())]

        # Perform ANOVA
        f_stat, p_value = f_oneway(*prices_by_rating)

        st.write(f"**F-statistic:** {f_stat:.4f}")
        st.write(f"**P-value:** {p_value:.4f}")

        if p_value < 0.05:
            st.success("✅ There are **significant differences** in book prices across ratings (reject H0).")
        else:
            st.info("ℹ️ No significant differences in prices across ratings (fail to reject H0).")

        # Basic statistics
        st.subheader('📈 Basic Descriptive Statistics')
        st.write(df.describe())

        # Rating distribution
        st.subheader('📊 Rating Distribution')
        rating_dist = df['Rating'].value_counts().sort_index()
        st.bar_chart(rating_dist)

        st.caption("👉 Shows how many books have each star rating.")

    else:
        st.warning("Please scrape the data first.")

if st.button('📊 Show Price Distribution'):
    if df is not None:
        fig_price_dist, ax = plt.subplots(figsize=(10, 6))
        ax.hist(df['Price'], bins=20, edgecolor='black')
        ax.set_title('Price Distribution of Books')
        ax.set_xlabel('Price (£)')
        ax.set_ylabel('Number of Books')
        st.pyplot(fig_price_dist)
    else:
        st.warning('Please scrape the data first.')

if st.button('💸 Relationship between Price and Rating'):
    if df is not None:
        st.subheader('💸 Relationship between Price and Rating')
        fig_price_rating_box, ax = plt.subplots(figsize=(10, 6))
        df.boxplot(column='Price', by='Rating', grid=False, ax=ax)
        fig_price_rating_box.suptitle('')
        ax.set_xlabel('Star Rating')
        ax.set_ylabel('Price (£)')
        st.pyplot(fig_price_rating_box)
    else:
        st.warning('Please scrape the data first.')

if st.button('⭐ Show Rating Distribution'):
    if df is not None:
        fig_rating_dist, ax = plt.subplots(figsize=(8, 6))
        df['Rating'].value_counts().sort_index().plot(kind='bar', ax=ax)
        ax.set_title('Book Rating Distribution')
        ax.set_xlabel('Star Rating')
        ax.set_ylabel('Number of Books')
        st.pyplot(fig_rating_dist)
    else:
        st.warning('Please scrape the data first.')

if st.button('🔥 Correlation between Price and Rating'):
    if df is not None:
        correlation = df[['Price', 'Rating']].corr()
        st.write(correlation)

        fig_corr_heatmap, ax = plt.subplots(figsize=(6, 4))
        sns.heatmap(correlation, annot=True, cmap='coolwarm', vmin=-1, vmax=1)
        ax.set_title('Correlation Heatmap')
        st.pyplot(fig_corr_heatmap)
    else:
        st.warning('Please scrape the data first.')

if st.button('📈 Average Price Per Rating'):
    if df is not None:
        avg_price_by_rating = df.groupby('Rating')['Price'].mean().reset_index()
        fig_avg_price, ax = plt.subplots(figsize=(10, 6))
        sns.lineplot(data=avg_price_by_rating, x='Rating', y='Price', marker='o', ax=ax)
        ax.set_title('Average Price per Rating')
        ax.set_xlabel('Star Rating')
        ax.set_ylabel('Average Price (£)')
        st.pyplot(fig_avg_price)
    else:
        st.warning('Please scrape the data first.')

if st.button('💾 Save to MongoDB'):
    if df is not None:
        collection = save_to_mongodb(df)
        st.success('Data saved to MongoDB!')
        docs = list(collection.find().limit(5))
        st.subheader('📂 Sample from MongoDB')
        sample_df = pd.DataFrame(docs) # Optional: Drop Mongo's internal _id
        st.dataframe(sample_df)

    else:
        st.warning('Please scrape the data first.')

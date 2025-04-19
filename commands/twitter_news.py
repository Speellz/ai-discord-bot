from discord.ext import commands, tasks
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import discord
import time
import os
import json

TWITTER_ACCOUNTS = ["sputnik_TR", "bpthaber"]
CHECK_INTERVAL = 5  # dakika
CHANNEL_ID = 1348942178348433480
TWEET_HISTORY_FILE = "tweet_history.json"

class TwitterNews(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sent_tweets = self.load_sent_tweets()
        self.task_started = False
        self.driver = self.initialize_driver()

    def initialize_driver(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920x1080")
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def get_twitter_url(self, username):
        return f"https://x.com/{username}"

    def load_sent_tweets(self):
        if os.path.exists(TWEET_HISTORY_FILE):
            with open(TWEET_HISTORY_FILE, "r", encoding="utf-8") as f:
                try:
                    return set(json.load(f))
                except json.JSONDecodeError:
                    return set()
        return set()

    def save_sent_tweet(self, tweet_url):
        self.sent_tweets.add(tweet_url)
        with open(TWEET_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(list(self.sent_tweets), f, ensure_ascii=False, indent=2)

    def get_latest_tweet(self, username):
        try:
            url = self.get_twitter_url(username)
            self.driver.get(url)
            time.sleep(5)

            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 1500);")
                time.sleep(2)

            articles = self.driver.find_elements(By.XPATH, '//article')
            print(f"🔎 {username} hesabında {len(articles)} tweet bulundu.")

            for article in articles:
                try:
                    if article.find_elements(By.XPATH, './/span[contains(text(), "Sabitlenmiş Tweet")]'):
                        print("📌 Sabitlenmiş tweet atlandı.")
                        continue

                    tweet_text_el = article.find_element(By.XPATH, './/div[@data-testid="tweetText"]')
                    tweet_text = tweet_text_el.text

                    tweet_link_el = article.find_element(By.XPATH, './/a[contains(@href, "/status/")]')
                    tweet_link = tweet_link_el.get_attribute("href")

                    if tweet_link in self.sent_tweets:
                        print(f"🔁 Tweet zaten gönderilmiş: {tweet_link}")
                        continue

                    video_url = None
                    try:
                        video_el = article.find_element(By.XPATH, './/video/source')
                        video_url = video_el.get_attribute("src")
                        if "blob:" in video_url:
                            print(f"⚠️ {username} video blob formatında, kullanılmayacak.")
                            video_url = None
                    except:
                        print(f"⚠️ {username} için video bulunamadı.")

                    image_urls = []
                    if not video_url:
                        image_els = article.find_elements(By.XPATH, './/img[contains(@src, "twimg.com/media")]')
                        image_urls = [img.get_attribute("src") for img in image_els]

                    print(f"✅ Yeni tweet bulundu: {tweet_text[:50]}... - {tweet_link}")
                    return tweet_text, tweet_link, image_urls, video_url

                except Exception as e:
                    print(f"⚠️ Tweet analizi başarısız oldu: {e}")
                    continue

            print("❌ Hiçbir yeni tweet bulunamadı.")
            return None, None, [], None

        except Exception as e:
            print(f"❌ Genel hata: {e}")
            return None, None, [], None

    @tasks.loop(minutes=CHECK_INTERVAL)
    async def check_tweets(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(CHANNEL_ID)

        for account in TWITTER_ACCOUNTS:
            print(f"🔍 {account} için kontrol başlatıldı.")
            tweet_text, tweet_link, image_urls, video_url = self.get_latest_tweet(account)

            if not tweet_text or not tweet_link:
                print(f"ℹ️ {account} için geçerli tweet bulunamadı.")
                continue

            if tweet_link in self.sent_tweets:
                print(f"🔁 {account} tweet daha önce gönderilmiş.")
                continue

            self.save_sent_tweet(tweet_link)

            embed = discord.Embed(title=f"{account} Yeni Tweet", description=tweet_text, color=0x1DA1F2)
            embed.add_field(name="Tweet Linki", value=f"[Görüntüle]({tweet_link})")
            if image_urls:
                embed.set_image(url=image_urls[0])

            await channel.send(embed=embed)
            print(f"📢 {account} tweeti gönderildi: {tweet_link}")

    async def start_task(self):
        if not self.task_started:
            self.check_tweets.start()
            self.task_started = True

    def cog_unload(self):
        if self.driver:
            self.driver.quit()
            print("🛑 TwitterNews driver kapatıldı.")

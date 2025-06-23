from discord.ext import commands, tasks
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import discord
import time
import os
import json

TWITTER_ACCOUNTS = ["sputnik_TR", "bpthaber"]
CHECK_INTERVAL = 5
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

    def get_new_tweets(self, username):
        try:
            url = self.get_twitter_url(username)
            self.driver.get(url)
            time.sleep(5)

            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 1500);")
                time.sleep(2)

            articles = self.driver.find_elements(By.XPATH, '//article')
            print(f"🔎 {username} hesabında {len(articles)} tweet bulundu.")

            new_tweets = []

            for article in articles:
                try:
                    if any("Sabit" in el.text for el in article.find_elements(By.XPATH, './/span')):
                        continue

                    tweet_text_el = article.find_element(By.XPATH, './/div[@data-testid="tweetText"]')
                    tweet_text = tweet_text_el.text

                    tweet_links = article.find_elements(By.XPATH, './/a[contains(@href, "/status/")]')
                    if not tweet_links:
                        continue
                    tweet_link = tweet_links[0].get_attribute("href")

                    if tweet_link in self.sent_tweets:
                        continue

                    video_url = None
                    try:
                        video_el = article.find_element(By.XPATH, './/video/source')
                        video_url = video_el.get_attribute("src")
                        if "blob:" in video_url:
                            video_url = None
                    except:
                        pass

                    image_urls = []
                    if not video_url:
                        image_els = article.find_elements(By.XPATH, './/img[contains(@src, "twimg.com/media")]')
                        image_urls = [img.get_attribute("src") for img in image_els]

                    new_tweets.append((tweet_text, tweet_link, image_urls, video_url))
                    print(f"📌 Yeni tweet bulundu: {tweet_text[:40]}... | {tweet_link}")

                except Exception as e:
                    print(f"⚠️ Tweet ayrıştırılırken hata: {e}")
                    continue

            return new_tweets

        except Exception as e:
            print(f"❌ Genel hata: {e}")
            return []

    @tasks.loop(minutes=CHECK_INTERVAL)
    async def check_tweets(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(CHANNEL_ID)

        for account in TWITTER_ACCOUNTS:
            print(f"🔍 {account} için kontrol başlatıldı.")
            new_tweets = self.get_new_tweets(account)

            if not new_tweets:
                print(f"ℹ️ {account} için yeni tweet yok.")
                continue

            for tweet_text, tweet_link, image_urls, video_url in reversed(new_tweets):
                if tweet_link in self.sent_tweets:
                    continue

                embed = discord.Embed(title=f"{account} Yeni Tweet", description=tweet_text, color=0x1DA1F2)
                embed.add_field(name="Tweet Linki", value=f"[Görüntüle]({tweet_link})")
                if image_urls:
                    embed.set_image(url=image_urls[0])

                try:
                    await channel.send(embed=embed)
                    self.save_sent_tweet(tweet_link)
                    print(f"📢 {account} tweeti gönderildi: {tweet_link}")
                except Exception as e:
                    print(f"❌ Mesaj gönderilirken hata oluştu: {e}")

    async def start_task(self):
        if not self.task_started:
            self.check_tweets.start()
            self.task_started = True

    def cog_unload(self):
        if self.driver:
            self.driver.quit()
            print("🛑 TwitterNews driver kapatıldı.")

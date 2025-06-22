import os
import json
import time
import discord
from discord.ext import commands, tasks
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

TWITTER_ACCOUNTS = ["sputnik_TR", "bpthaber"]
CHECK_INTERVAL = 5  # minutes
CHANNEL_ID = 1348942178348433480
TWEET_HISTORY_FILE = "tweet_history.json"


class TwitterNews(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sent_tweets = self.load_sent_tweets()
        self.driver = self.initialize_driver()
        self.check_tweets.start()

    def initialize_driver(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920x1080")
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def load_sent_tweets(self):
        if os.path.exists(TWEET_HISTORY_FILE):
            with open(TWEET_HISTORY_FILE, "r", encoding="utf-8") as f:
                try:
                    return set(json.load(f))
                except json.JSONDecodeError:
                    return set()
        return set()

    def save_sent_tweet(self, url: str):
        self.sent_tweets.add(url)
        with open(TWEET_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(list(self.sent_tweets), f, ensure_ascii=False, indent=2)

    def get_latest_tweet(self, username):
        try:
            self.driver.get(f"https://x.com/{username}")
            time.sleep(5)
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 1500);")
                time.sleep(2)
            articles = self.driver.find_elements(By.XPATH, '//article')
            for article in articles:
                try:
                    if article.find_elements(By.XPATH, './/span[contains(text(), "Sabitlenmiş Tweet")]'):
                        continue
                    tweet_text_el = article.find_element(By.XPATH, './/div[@data-testid="tweetText"]')
                    tweet_text = tweet_text_el.text
                    tweet_link_el = article.find_element(By.XPATH, './/a[contains(@href, "/status/")]')
                    tweet_link = tweet_link_el.get_attribute("href")
                    if tweet_link in self.sent_tweets:
                        continue
                    return tweet_text, tweet_link
                except Exception:
                    continue
        except Exception:
            return None, None
        return None, None

    @tasks.loop(minutes=CHECK_INTERVAL)
    async def check_tweets(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(CHANNEL_ID)
        for account in TWITTER_ACCOUNTS:
            text, link = self.get_latest_tweet(account)
            if not text or not link or link in self.sent_tweets:
                continue
            self.save_sent_tweet(link)
            embed = discord.Embed(title=f"{account} Yeni Tweet", description=text, color=0x1DA1F2)
            embed.add_field(name="Tweet", value=f"[Link]({link})")
            if channel:
                await channel.send(embed=embed)

    def cog_unload(self):
        if self.driver:
            self.driver.quit()

async def setup(bot: commands.Bot):
    await bot.add_cog(TwitterNews(bot))

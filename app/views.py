from django.views.generic import View
from django.shortcuts import render, redirect
from django.conf import settings
from .forms import TweetForm
from datetime import datetime, timedelta
import tweepy
import pandas as pd
import json


# Twitter API認証
TWEEPY_AUTH = tweepy.OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
TWEEPY_AUTH.set_access_token(settings.ACCESS_KEY, settings.ACCESS_KEY_SECRET)
# API利用制限にかかった場合、解除まで待機する
TWEEPY_API = tweepy.API(TWEEPY_AUTH, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)


# ツイートを収集する関数
def get_search_tweet(s, items_count, rlcount, since, until):
    '''
    ツイート情報を期間指定で収集
    取得できるのデータは1週間以内の分だけ
    リツイート数＋いいね数の合計でツイートを絞り込める
    '''
    # q：キーワード
    # since：いつから
    # until：いつまで,
    # tweet_mode：つぶやきの省略ありなし
    # lang：言語
    # .itemes(数)：ツイート数を指定
    tweets = tweepy.Cursor(
        TWEEPY_API.search,
        q=s + '-filter:retweets',
        exclude_replies=True,
        since=since,
        until=until,
        tweet_mode='extended',
        lang='ja'
    ).items(items_count)

    # ツイートのデータを取り出して、リストにまとめていく部分
    # ツイートデータを入れる空のリストを用意
    tweet_data = []
    # 日付ごとにデータの合計を格納する
    favorite_data = {}
    retweet_data = {}
    post_data = {}
    date_tmp = ''
    favorite_data_count = 0
    retweet_data_count = 0
    post_data_count = 0
    for tweet in tweets:
        # いいねとリツイートの合計がrlcuont以上の条件
        if tweet.favorite_count + tweet.retweet_count >= rlcount:
            # UTC時間なので日本時間に直すために9時間プラス
            tweet.created_at += timedelta(hours=9)
            created_at = tweet.created_at.strftime('%Y-%m-%d %H:%M')

            # 日付ごとにいいねとリツイート数、投稿数の合計を計算
            date = tweet.created_at.strftime('%Y-%m-%d')
            if date_tmp == date:
                favorite_data_count += tweet.favorite_count
                retweet_data_count += tweet.retweet_count
                post_data_count += 1
            else:
                date_tmp = date
                favorite_data_count = tweet.favorite_count
                retweet_data_count = tweet.retweet_count
                post_data_count = 1
            # 辞書型なので、同じキーはアップデートされる
            favorite_data[date] = favorite_data_count
            retweet_data[date] = retweet_data_count
            post_data[date] = post_data_count

            # メディアがある場合とない場合
            try:
                media_url = tweet.entities['media'][0]['media_url_https']
            except KeyError: # 辞書内に指定したキーが存在しない
                media_url = ''

            # ツイートのデータを追加
            tweet_data.append([
                tweet.user.name, # 名前
                tweet.user.screen_name, # スクリーンネーム
                tweet.user.profile_image_url, # プロフィール画像
                media_url, # メディア
                tweet.full_text, # 本文
                tweet.retweet_count, # リツイート数
                tweet.favorite_count, # いいね数
                created_at, # ツイート日
            ])

    return tweet_data, favorite_data, retweet_data, post_data


def make_df(data):
    '''
    ツイートデータからDataframeを作成する
    '''
    name = []
    screen_name = []
    profile_image_url = []
    media_url = []
    full_text = []
    retweet_count = []
    favorite_count = []
    created_at = []

    # ツイートデータデータごとにまとめたリストを作る
    for i in range(len(data)):
        name.append(data[i][0])
        screen_name.append(data[i][1])
        profile_image_url.append(data[i][2])
        media_url.append(data[i][3])
        full_text.append(data[i][4])
        retweet_count.append(data[i][5])
        favorite_count.append(data[i][6])
        created_at.append(data[i][7])

    # 結合するために一旦Seriesにする
    df_name = pd.Series(name)
    df_screen_name = pd.Series(screen_name)
    df_profile_image_url = pd.Series(profile_image_url)
    df_media_url = pd.Series(media_url)
    df_full_text = pd.Series(full_text)
    df_retweet_count = pd.Series(retweet_count)
    df_favorite_count = pd.Series(favorite_count)
    df_created_at = pd.Series(created_at)

    # 列で横に結合
    df = pd.concat([
        df_name,
        df_screen_name,
        df_profile_image_url,
        df_media_url,
        df_full_text,
        df_retweet_count,
        df_favorite_count,
        df_created_at
    ], axis=1)

    # カラムをつける
    df.columns = [
        'name',
        'screen_name',
        'profile_image_url',
        'media_url',
        'full_text',
        'retweet_count',
        'favorite_count',
        'created_at'
    ]

    return df


class IndexView(View):
    def get(self, request, *args, **kwargs):
        # 検索フォーム
        form = TweetForm(
            request.POST or None,
            # フォームに初期値を設定
            initial={
                'items_count': 100, # 検索数
                'rlcount': 1, # いいねリツイート合計数
                'search_start': datetime.today() - timedelta(days=7), # 一週間前
                'search_end': datetime.today(), # 本日
            }
        )

        return render(request, 'app/index.html', {
            'form': form
        })

    def post(self, request, *args, **kwargs):
        # キーワード検索して、いいね、ツイートが多いものを表示
        form = TweetForm(request.POST or None)

        # フォームのバリデーション
        if form.is_valid():
            # フォームからデータを取得
            keyword = form.cleaned_data['keyword']
            items_count = form.cleaned_data['items_count']
            rlcount = form.cleaned_data['rlcount']
            search_start = form.cleaned_data['search_start']
            search_end = form.cleaned_data['search_end']

            # ツイート検索
            data = get_search_tweet(keyword, items_count, rlcount, search_start, search_end)
            tweet_data = data[0]
            favorite_data = data[1]
            retweet_data = data[2]
            post_data = data[3]

            # グラフデータをまとめる
            graph_data = {
                'date': list(favorite_data.keys()),
                'favorite_data': list(favorite_data.values()),
                'retweet_data': list(retweet_data.values()),
                'post_data': list(post_data.values()),
            }

            # ツイートデータをデータフレーム化する
            tweet_data = make_df(tweet_data)

            # API使用制限取得
            limit = TWEEPY_API.last_response.headers['x-rate-limit-remaining']

            return render(request, 'app/tweet.html', {
                'keyword': keyword,
                'tweet_data': tweet_data,
                'limit': limit,
                'graph_data': json.dumps(graph_data),
            })
        else:
            # バリデーションが失敗した場合はトップページへ
            return redirect('index')

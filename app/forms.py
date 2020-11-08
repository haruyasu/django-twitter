from django import forms


class TweetForm(forms.Form):
    keyword = forms.CharField(max_length=30, label='キーワード')
    count = forms.CharField(max_length=30, label='いいねリツイート数')
    search_start = forms.DateField(widget=forms.DateInput(attrs={"type":'date'}), label='検索開始日')
    search_end = forms.DateField(widget=forms.DateInput(attrs={"type":'date'}), label='検索終了日')

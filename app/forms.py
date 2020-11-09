from django import forms


class TweetForm(forms.Form):
    keyword = forms.CharField(max_length=30, label='キーワード')
    items_count = forms.IntegerField(label='検索数')
    rlcount = forms.IntegerField(label='いいねリツイート数')
    search_start = forms.DateField(widget=forms.DateInput(attrs={"type":'date'}), label='検索開始日')
    search_end = forms.DateField(widget=forms.DateInput(attrs={"type":'date'}), label='検索終了日')

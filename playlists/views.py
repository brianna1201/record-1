from django.shortcuts import render, redirect, get_object_or_404
from .models import Playlist, Comment
from musics.models import Music
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from users.models import User
import pdb
import json
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.serializers.json import DjangoJSONEncoder
from datetime import datetime
from django.forms.models import model_to_dict


# 플레이리스트 메인페이지
def main(request):
    playlists_list = Playlist.objects.filter(kinds=0).order_by('-id')
    tags = Playlist.tags.all()[:5]

    page = request.GET.get('page', 1)
    paginator = Paginator(playlists_list, 9)
    try:
        playlists = paginator.page(page)
    except PageNotAnInteger:
        playlists = paginator.page(1)
    except EmptyPage:
        playlists = paginator.page(paginator.num_pages)

    return render(request, 'playlists/main.html', {'playlists': playlists, 'tags': tags})


# 상세보기페이지
def show(request, id):
    playlist = get_object_or_404(Playlist, pk=id)
    return render(request, 'playlists/show.html', {'playlist': playlist})


# 플레이리스트 수정하기
def edit(request, id):
    user = request.user
    playlist = get_object_or_404(Playlist, pk=id)

    if user == playlist.creator:
        tags = playlist.tags.all()
        content = ""
        
        for tag in tags:
            content += str(tag)+','
            playlist.tags.remove(tag)

        content = content[:-1]

        return render(request, 'playlists/edit.html', {"playlist": playlist, 'content': content })
    else:
        return redirect('playlists:show', id)


def update(request, id):
    playlist = get_object_or_404(Playlist, pk=id)

    if request.method == "POST":
        playlist.kinds = request.POST.get('kinds')
        tags = request.POST.get('tags')
        
        list=[]
        list = tags.split(',')
        
        for tag in list:
            if tag != "":
                words =""
                if tag.find(' ') == 0:
                    for word in tag:
                        if word != ' ':
                            words += word
                    playlist.tags.add(words)
                else:
                    playlist.tags.add(tag)
        
        if request.FILES.get('cover'):
            playlist.cover = request.FILES.get('cover')

        playlist.title = request.POST.get('title')
        playlist.description = request.POST.get('description')
        playlist.save()

    return redirect('playlists:show', id)


# 플레이리스트 삭제하기
def delete(request, id):
    playlist = get_object_or_404(Playlist, pk=id)
    playlist.delete()
    return redirect('playlists:main')



# 댓글생성
@require_POST
@login_required
def create_comment(request, playlist_id):
    user = request.user
    if user.is_anonymous:
        return redirect('account_login')

    if request.method == "POST":
        playlist = get_object_or_404(Playlist, pk=playlist_id)
        message = request.POST.get('message')
        comment = Comment.objects.create(writer=user, playlist=playlist, message=message)

        context = {
            'writer': user.username,
            'message': comment.message,
            'is_same': user == comment.writer,
            'comment_pk': comment.pk,
            'created_at': comment.created_at.strftime('%Y/%m/%d %H:%M'),
            'writer_id': comment.writer.id,
            'writer_image_url': comment.writer.image.url
        }
        return HttpResponse(json.dumps(context, cls=DjangoJSONEncoder))


# 댓글삭제
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    playlist_id = comment.playlist.id
    comment.delete()
    return redirect('playlists:show', playlist_id)


# 좋아요
@require_POST
@login_required
def like_toggle(request, playlist_id):
    playlist = get_object_or_404(Playlist, pk=playlist_id)
    playlist_like, playlist_like_created = playlist.like_set.get_or_create(creator=request.user)

    if not playlist_like_created:
        playlist_like.delete()
        result = "like_cancel"
    else:
        result ="like"

    context = {
        'likes_count':playlist.likes_count,
        'result': result
    }    

    return HttpResponse(json.dumps(context), content_type="application/json")

# 태그 검색
def tag(request, tag_id):
    tags = Playlist.tags.all()[:5]

    tag = Playlist.tags.get(pk=tag_id)
    playlists_list = Playlist.objects.filter(tags__name__in=[tag], kinds=0)
    # page = request.GET.get('page', 1)
    paginator = Paginator(playlists_list, 9)

    try:
        page = int(request.GET.get('page','1'))
    except:
        page = 1

    try:
        playlists = paginator.page(page)
    except PageNotAnInteger:
        playlists = paginator.page(1)
    except EmptyPage:
        playlists = paginator.page(paginator.num_pages)

    return render(request, 'playlists/tag.html', {'playlists': playlists, 'tags': tags})


# 음악 삭제하기
def delete_music(request, playlist_id, music_id):
    playlist = get_object_or_404(Playlist, pk=playlist_id)
    music = get_object_or_404(Music, pk=music_id)
    playlist.musics.remove(music)
    return redirect('playlists:show', playlist_id)

# 검색
def search(request):
    tags = Playlist.tags.all()[:5]
    query = request.GET.get('query')
    search_list = Playlist.objects.filter(title__contains=query)
    # page = request.GET.get('page')
    paginator = Paginator(search_list, 9)
    
    try:
        page = int(request.GET.get('page','1'))
    except:
        page = 1

    try:
        search_result = paginator.get_page(page)
    except PageNotAnInteger:
        search_result = paginator.get_page(1)
    except EmptyPage:
        search_result = paginator.page(paginator.num_pages)
    return render(request, 'playlists/search.html', {'search_result': search_result, 'search_list': search_list, 'tags': tags})


# 새 플레이리스트 생성 페이지
def new(request):
    user = request.user
    if user.is_anonymous:
        return redirect('account_login')
    else:
        return render(request,'playlists/new.html')


# 새 플레이리스트 생성
def create(request):
    user = request.user
    if user.is_anonymous:
        return redirect('account_login')

    if request.method == "POST":
        playlist = Playlist()
        playlist.creator = user
        playlist.title = request.POST.get('title')
        playlist.description = request.POST.get('description')
        playlist.kinds = request.POST.get('kinds')
        tags = request.POST.get('tags')
        
        if request.FILES.get('cover'):
            playlist.cover = request.FILES.get('cover')
        
        playlist.save()
    
        list=[]
        list = tags.split(',') 
        
        for tag in list:
            if tag != "":
                words =""
                if tag.find(' ') == 0:
                    for word in tag:
                        if word != ' ':
                            words += word
                    playlist.tags.add(words)
                else:
                    playlist.tags.add(tag)

        music_id = request.POST.get('music_id')
        music = Music.objects.get(pk=music_id)
        playlist.musics.add(music)
    
    return redirect('playlists:show', playlist.id)

    
# 팔로우, 언팔로우
# def follow_toggle(request, id):
#     user = request.user
#     if user.is_anonymous:
#         return redirect('account_login')
    

#     playlist = get_object_or_404(Playlist, pk=id)
#     followed_user = get_object_or_404(User, pk=playlist.creator.id)

#     is_follower = user in followed_user.followers.all()

#     if is_follower:
#         user.followings.remove(followed_user)
#     else:
#         user.followings.add(followed_user)

#     return redirect('playlists:show', id)

# 팔로우, 언팔로우
@login_required
@require_POST
def follow_toggle(request, id):
    # user = request.user
    # if user.is_anonymous:
    #     return redirect('account_login')
    
    followed_user = get_object_or_404(User, pk=id)
    followers = followed_user.followers.set()
    following_already, following_created = followed_user.followers.get_or_create(followers=request.user)

    # is_follower = user in followed_user.followers.all()

    # if is_follower:
    #     user.followings.remove(followed_user)
    # else:
    #     user.followings.add(followed_user)

    if not following_created:
        follwoing_already.delete()
        result = "following cancel"
    else:
        result = "following"
    
    context = {'result':result}

    return HttpResponse(json.dumps(context), content_type="application/json")

    # return redirect('users:main', id)
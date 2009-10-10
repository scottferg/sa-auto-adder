from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, loader
from google.appengine.ext import db
from models import User
from appengine_utilities import sessions
import utils, datetime, hashlib, random, urllib

def valid_sa_user_id(user_id):
  try:
    uid = int(user_id)
  except ValueError:
    return False
  return uid > 0
  
def check_auth_token(user_id):
  if not valid_sa_user_id(user_id):
    return (False, 'invalid user id')
  url = "http://forums.somethingawful.com/member.php?action=getinfo&userid=%s" % user_id
  session = sessions.Session()
  error = None
  found_token = False
  data = None
  try:
    f = urllib.urlopen(url)
    data = f.read()
    found_token = session['token'] in f.read()
  except:
    error = 'couldn\'t read website'
  finally:
    f.close()
  if found_token == False:
    error = 'couldn\'t find token (%s) (%s)' % (session['token'], data)
  return (found_token, error)
  

def create_token():
  session = sessions.Session()
  token = "sa-auto-adder|%s" % hashlib.sha1(str(random.random())).hexdigest()[:10]
  
  token = "sa-auto-adder|test"
  
  session['token'] = token
  return token

def logout(redirect_to):
  session = sessions.Session()
  response = HttpResponseRedirect(redirect_to)
  query = db.Query(User)
  if "username" in session:
    query.filter("username =",session['username'])
    user = query.get()
    if user is not None:
      user.cookie_token = ""
      user.put()
  session.delete()
  response['Set-Cookie'] = "token=; expires=Thu, 01-Jan-1970 00:00:01 GMT"
  return response

def login(user, redirect_to, set_cookie):
  session = sessions.Session()
  session['username'] = user.username
  user.last_login = datetime.datetime.now()
  response = HttpResponseRedirect(redirect_to)  
  if set_cookie:
    utils.set_cookie_header(response, user)    
  user.put()
  return response
  
def set_cookie_header(response, user):
  cookie_token = hashlib.sha1(str(random.random())).hexdigest()
  cookie_value = "token=%s|%s; expires=Fri, 31-Dec-2020 23:59:59 GMT" % (cookie_token, user.username)
  response['Set-Cookie'] = cookie_value
  user.cookie_token = cookie_token

def require_login(method):
  def new(request):
    session = sessions.Session()
    if 'username' in session:
      return method(request)

    if "token" in request.COOKIES:
      if check_cookie_token(request.COOKIES["token"]):
        session['username'] = request.COOKIES["token"].split('|')[1]
        return method(request)
        
    return HttpResponseRedirect('/')
  return new

def authenticate(username, password):
  import hashlib
  query = db.Query(User)
  query.filter('username =', username)
  query.filter('password =', hashlib.sha1(password).hexdigest())
  return query.get()

def check_cookie_token(token):
  cookie_token, username = token.split('|')
  query = db.Query(User)
  query.filter('username =', username)
  query.filter('cookie_token =', cookie_token)
  return query.get() != None

def redirect_if_authenticated(url):
  def redirect(method):
    def new(request):
      session = sessions.Session()
      if 'username' in session:
        return HttpResponseRedirect(url)

      if "token" in request.COOKIES:
        if check_cookie_token(request.COOKIES["token"]):
          session['username'] = request.COOKIES["token"].split('|')[1]
          return HttpResponseRedirect(url)
      return method(request)
    return new  
  return redirect
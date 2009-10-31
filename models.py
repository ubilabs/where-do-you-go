from google.appengine.ext import db

class Token(db.Model):
  owner = db.UserProperty()
  created = db.DateTimeProperty(auto_now_add=True)
  token = db.StringProperty()
  secret = db.StringProperty()

class Venue(db.Model):
  venue_id = db.IntegerProperty()
  name = db.StringProperty()
  address = db.StringProperty()
  crossstreet = db.StringProperty()
  city = db.StringProperty()
  state = db.StringProperty()
  zipcode = db.IntegerProperty()
  geolat = db.FloatProperty()
  geolong = db.FloatProperty()
  phone = db.PhoneNumberProperty()

class Checkin(db.Model):
  user = db.UserProperty()
  checkin_id = db.IntegerProperty()
  created = db.DateTimeProperty()
  venue =  db.ReferenceProperty(Venue)
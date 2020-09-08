from app import db
from app import models
db.drop_all()
db.create_all()
user = models.User(username="arthur", email="arthur.hjorth@stx.oxon.org")
pw = models.User.set_password(user, "arthur")
db.session.add(user)
activity = models.Activity(name="High Score", owner=1, password="test1234", template="highscore.html")
db.session.add(activity)
db.session.commit()


from app import db
from app import models

db.drop_all()
db.create_all()



user = models.User(username="arthurhjorth", email="arthur.hjorth@stx.oxon.org")
pw = models.User.set_password(user, "arthur")

db.session.add(user)

activity = models.Activity(name="High Score", owner=1)
db.session.add(activity)
db.session.commit()


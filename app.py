from time import process_time
from flask import Flask, render_template, request, flash, redirect, url_for
from sqlalchemy import desc
from models import db, Artist, Show, Venue
from flask_migrate import Migrate
from forms import *
from logging import Formatter, FileHandler
import logging
from flask_sqlalchemy import SQLAlchemy
from flask_moment import Moment
import babel
from datetime import datetime
from dateutil import parser
import json
import flask_wtf
import collections
collections.Callable = collections.abc.Callable


app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)
migrate = Migrate(app, db)
migrate.init_app(app, db)

with app.app_context():
    db.create_all()


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    artists = []
    venues = []

    try:
        recently_listed_artists = Artist.query.order_by(
            desc(Artist.created_at_timestamp)).limit(10).all()

        recently_listed_venues = Venue.query.order_by(
            desc(Venue.created_at_timestamp)).limit(10).all()

        for artist in recently_listed_artists:
            artists.append({"name": artist.name})

        for venue in recently_listed_venues:
            venues.append({"name": venue.name})
    except:
        flash("Failed to fetch data. The database might not be running")

    return render_template('pages/home.html', artists=artists, venues=venues)


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data = []
    try:
        venues = Venue.query.all()

        # We use a set to unsure that the same location will be considered only once
        # e.g: locations = {
        #   ("San Francisco", "CA"),
        #   ("New York", "NY")
        # }
        locations_set = set()

        # Get all states and cities of all venues stored in the database
        for venue in venues:
            locations_set.add((venue.city, venue.state))

        locations = list(locations_set)

        for location in locations:
            venues = Venue.query.filter_by(
                city=location[0], state=location[1])
            formated_venues = []
            for venue in venues:
                formated_venues.append(
                    {
                        "id": venue.id,
                        "name": venue.name,
                        "num_upcoming_shows": len(venue.shows)
                    }
                )
            formated_data = {
                "city": location[0],
                "state": location[1],
                "venues": formated_venues
            }
            data.append(formated_data)
    except:
        flash('Could not fetch venues, the database might not be running.')
    finally:
        return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    data = []
    venues = Venue.query.filter(Venue.name.ilike(r"%{}%".format(
        request.form.get('search_term')))).all()

    for venue in venues:
        num_upcoming_shows = 0

        if venue.shows:
            for show in venue.shows:
                if datetime.today() < datetime.strptime(show.start_time, "%Y-%m-%d %H:%M:%S"):
                    num_upcoming_shows += 1

        data.append({
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": num_upcoming_shows
        })
    response = {
        "count": len(data),
        "data": data
    }

    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    data = {}
    try:
        venue = Venue.query.get(venue_id)
        venue_upcoming_shows = []
        venue_past_shows = []

        for show in venue.shows:
            artist = show.Artist
            if datetime.today() < datetime.strptime(show.start_time, "%Y-%m-%d %H:%M:%S"):
                venue_upcoming_shows.append({
                    "artist_id": artist.id,
                    "artist_name": artist.name,
                    "artist_image_link": artist.image_link,
                    "start_time": show.start_time
                })
            else:
                venue_past_shows.append({
                    "artist_id": artist.id,
                    "artist_name": artist.name,
                    "artist_image_link": artist.image_link,
                    "start_time": show.start_time
                })
        data = {
            "id": venue.id,
            "name": venue.name,
            "genres": json.loads(venue.genres),
            "address": venue.address,
            "city": venue.city,
            "state": venue.state,
            "phone": venue.phone,
            "website": venue.website_link,
            "facebook_link": venue.facebook_link,
            "seeking_talent": venue.seeking_talent,
            "seeking_description": venue.seeking_description,
            "image_link": venue.image_link,
            "past_shows": venue_past_shows,
            "upcoming_shows": venue_upcoming_shows,
            "past_shows_count": len(venue_past_shows),
            "upcoming_shows_count": len(venue_upcoming_shows),
        }
    except:
        flash('Could not fetch the venue, the database might not be running.')
    finally:
        return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():

    form = VenueForm(data=request.form)
    form.genres.data = json.dumps(request.form.getlist("genres"))
    try:
        new_venue = Venue(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            address=form.address.data,
            phone=form.phone.data,
            image_link=form.image_link.data,
            facebook_link=form.facebook_link.data,
            website_link=form.website_link.data,
            seeking_talent=form.seeking_talent.data,
            seeking_description=form.seeking_description.data,
            genres=form.genres.data
        )
        db.session.add(new_venue)
        db.session.commit()

        # on successful db insert, flash success
        flash('Venue ' + request.form['name'] +
              ' was successfully listed!')
    except:
        db.session.rollback()
        flash('An error occurred. Venue ' +
              request.form['name'] + ' could not be listed.')
    finally:
        db.session.close()
        return redirect(url_for('index'))
        # return render_template('pages/home.html')


@app.route('/venues/<venue_id>/delete', methods=['GET'])
def delete_venue(venue_id):
    try:
        venue = Venue.query.get(venue_id)
        db.session.delete(venue)
        db.session.commit()
        flash(
            f"The venue {venue.name} has been deleted from the database")
    except:
        db.session.rollback()
        flash(
            f"An error occured. Could not delete the venue with the id : {venue_id}")
    finally:
        db.session.close()
        return redirect(url_for('index'))

#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
    data = []
    try:
        artists = Artist.query.all()
        for artist in artists:
            data.append({
                "id": artist.id,
                "name": artist.name
            })
    except:
        flash('Could not fetch artists, the database might not be running.')
    finally:
        return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    data = []
    artists = Artist.query.filter(Artist.name.ilike(r"%{}%".format(
        request.form.get('search_term')))).all()

    for artist in artists:
        num_upcoming_shows = 0

        if artist.shows:
            for show in artist.shows:
                if datetime.today() < datetime.strptime(show.start_time, "%Y-%m-%d %H:%M:%S"):
                    num_upcoming_shows += 1

        data.append({
            "id": artist.id,
            "name": artist.name,
            "num_upcoming_shows": num_upcoming_shows
        })
    response = {
        "count": len(data),
        "data": data
    }
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    data = {}
    try:
        artist = Artist.query.get(artist_id)
        artist_upcoming_shows = []
        artist_past_shows = []

        if artist.shows:
            for show in artist.shows:
                venue = show.Venue
                if datetime.today() < datetime.strptime(show.start_time, "%Y-%m-%d %H:%M:%S"):
                    artist_upcoming_shows.append({
                        "venue_id": venue.id,
                        "venue_name": venue.name,
                        "venue_image_link": venue.image_link,
                        "start_time": show.start_time
                    })
                else:
                    artist_past_shows.append({
                        "venue_id": venue.id,
                        "venue_name": venue.name,
                        "venue_image_link": venue.image_link,
                        "start_time": show.start_time
                    })
        data = {
            "id": artist.id,
            "name": artist.name,
            "genres": json.loads(artist.genres),
            "city": artist.city,
            "state": artist.state,
            "phone": artist.phone,
            "website": artist.website_link,
            "facebook_link": artist.facebook_link,
            "seeking_venue": artist.seeking_venue,
            "seeking_description": artist.seeking_description,
            "image_link": artist.image_link,
            "past_shows": artist_past_shows,
            "upcoming_shows": artist_upcoming_shows,
            "past_shows_count": len(artist_past_shows),
            "upcoming_shows_count": len(artist_upcoming_shows),
        }
    except:
        flash(
            f"Could not fetch artist's informations, the database might not be running or an artist with the id {artist_id} doesn't exit.")
        return redirect(url_for('index'))

    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    try:
        artist = Artist.query.get(artist_id)
        data = {"id": artist.id,
                "name": artist.name,
                "genres": json.loads(artist.genres),
                "city": artist.city,
                "state": artist.state,
                "phone": artist.phone,
                "website": artist.website_link,
                "facebook_link": artist.facebook_link,
                "seeking_venue": artist.seeking_venue,
                "seeking_description": artist.seeking_description,
                "image_link": artist.image_link
                }
        form = ArtistForm(data=data)
        return render_template('forms/edit_artist.html', form=form, artist=artist)
    except:
        flash(
            f"Cannot edit the artist with the id : {artist_id}. The databse might not be running or such an Artist doesn't exist.")

    return redirect(url_for('index'))


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    form = ArtistForm(request.form)
    form.genres.data = json.dumps(request.form.getlist("genres"))
    try:
        db.session.query(Artist).filter(
            Artist.id == artist_id).update(
            form.data
        )
        db.session.commit()
        return redirect(url_for('show_artist', artist_id=artist_id))
    except:
        db.session.rollback()
        flash(f"Failed to update the artist {form.name.data}")
    finally:
        db.session.close
    return redirect(url_for('index'))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    try:
        venue = Venue.query.get(venue_id)
        data = {"id": venue.id,
                "name": venue.name,
                "address": venue.address,
                "genres": json.loads(venue.genres),
                "city": venue.city,
                "state": venue.state,
                "phone": venue.phone,
                "website": venue.website_link,
                "facebook_link": venue.facebook_link,
                "seeking_talent": venue.seeking_talent,
                "seeking_description": venue.seeking_description,
                "image_link": venue.image_link
                }
        form = VenueForm(data=data)
        return render_template('forms/edit_venue.html', form=form, venue=venue)
    except:
        flash(
            f"Cannot edit the venue with the id : {venue_id}. The databse might not be running or such an Venue doesn't exist.")

    return redirect(url_for('index'))


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    form = VenueForm(request.form)
    form.genres.data = json.dumps(request.form.getlist('genres'))
    try:
        db.session.query(Venue).filter(
            Venue.id == venue_id).update(
            form.data
        )
        db.session.commit()
        db.session.close()
        redirect(url_for('show_venue', venue_id=venue_id))
    except:
        db.session.rollback()
        flash(f"Could not update the venue {form.name.data}")
        db.session.close()
        return redirect(url_for('index'))
    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():

    artist = ArtistForm(data=request.form)
    try:
        new_artist = Artist(
            name=artist.name.data,
            city=artist.city.data,
            state=artist.state.data,
            phone=artist.phone.data,
            image_link=artist.image_link.data,
            facebook_link=artist.facebook_link.data,
            website_link=artist.website_link.data,
            seeking_venue=artist.seeking_venue.data,
            seeking_description=artist.seeking_description.data,
            genres=json.dumps(request.form.getlist("genres"))
        )

        db.session.add(new_artist)
        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except:
        flash('An error occurred. Artist ' +
              request.form["name"] + ' could not be listed.')
        db.session.rollback()
    finally:
        db.session.close()
    return redirect(url_for('index'))


#  Shows
#  ----------------------------------------------------------------

@ app.route('/shows')
def shows():
    data = []
    try:
        shows = Show.query.all()
        for show in shows:
            data.append({
                "venue_id": 1,
                "venue_name": show.Venue.name,
                "artist_id": show.Artist.id,
                "artist_name": show.Artist.name,
                "artist_image_link": show.Artist.image_link,
                "start_time": show.start_time
            })
    except:
        flash('Could not fetch Shows. The database might not be running.')
    finally:
        return render_template('pages/shows.html', shows=data)


@ app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@ app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm(request.form)
    try:
        new_show = Show(
            artist_id=form.artist_id.data,
            venue_id=form.venue_id.data,
            start_time=form.start_time.data
        )
        db.session.add(new_show)
        db.session.commit()
        flash('Show was successfully listed!')
    except:
        db.session.rollback()
        flash('An error occurred. Show could not be listed. This might be due to invalid IDs of Artist or Venue')
    finally:
        db.session.close()
        return redirect(url_for('index'))


@ app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@ app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''

import os

# logging
import logging
logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO)
# python-dotenv
from dotenv import load_dotenv
# spotipy
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def get_playlist_by_name(playlists, playlist_name):
    for playlist in playlists['items']:
        if playlist['name'] == playlist_name:
            return playlist
    return None

def split_tracks(tracks):
    clean_tracks = []
    explicit_tracks = []
    for track in tracks:
        if track['track']['explicit']:
            explicit_tracks.append(track['track'])
        else:
            clean_tracks.append(track['track'])
    return clean_tracks, explicit_tracks

def find_clean_track(sp, explicit_track):
    track_name = explicit_track['name']
    track_artist = explicit_track['artists'][0]['name']
    query_string = 'track:' + track_name + ' artist:' + track_artist
    search_results = sp.search(query_string, type='track')
    for track in search_results['tracks']['items']:
        if not track['explicit']:
            return track
    return None

def track_information(track):
    track_info = {}
    track_info['artist'] = track['artists'][0]['name']
    track_info['name'] = track['name']
    track_info['explicit'] = track['explicit']
    return track_info

# Load in Application Tokens from .env
logging.debug('Loading .env')
load_dotenv()
logging.debug('Loaded .env, environment is:')
logging.debug(os.environ)

# Initialise Spotipy
# Scope of the application that we need is the ability to modify playlists
scope = "playlist-modify-private,playlist-modify-public"
logging.info('Initialising Spotipy')
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
logging.info('Spotipy Ready')

# Get some of our user details that will help us out
user = sp.current_user()
user_id = user['id']
logging.debug(user)

# Get the users playlists
logging.info('Getting playlists')
playlists = sp.user_playlists(user_id)
# TODO: Take this as a CLI param
playlist_to_clean = input('Enter name of playlist to clean: ')
target_playlist = get_playlist_by_name(playlists, playlist_to_clean)

# Make sure we have a playlist
if target_playlist is None:
    logging.error('Playlist of name ' + playlist_to_clean + ' not found, exiting')
    exit(1)
else:
    logging.info('Playlist Found')
    
target_playlist_id = target_playlist['id']

# Find any explicit songs
logging.info('Getting tracks in playlist')
num_tracks = target_playlist['tracks']['total']
playlist_tracks = []
for i in range((num_tracks // 100)+1):
    playlist_tracks = playlist_tracks + sp.user_playlist_tracks(user=user_id, playlist_id=target_playlist_id, limit=100, offset=(i*100))['items']

#playlist_tracks = sp.user_playlist_tracks(user=user_id, playlist_id=target_playlist_id)
clean_tracks, explicit_tracks = split_tracks(playlist_tracks)
# Exit if none are found
if len(explicit_tracks) == 0:
    logging.info('Playlist contains no explicit songs!')
    exit(0)

# Now let's go find the replacements
tracks_added = []
for explicit_track in explicit_tracks:
    explicit_track_info = track_information(explicit_track)
    logging.info('Finding clean version of ' + explicit_track_info['name'] + ' by ' + explicit_track_info['artist'])
    clean_track = find_clean_track(sp, explicit_track)
    if clean_track is not None:
        logging.info('Clean track found')
        clean_tracks.append(clean_track)
        tracks_added.append(clean_track)
    else:
        logging.warning('No clean track found')

logging.info('Making a new playlist')
new_playlist_name = playlist_to_clean + ' (Clean)'
new_playlist = sp.user_playlist_create(user_id, new_playlist_name, public=True)
new_playlist_id = new_playlist['id']
logging.info('Adding clean tracks to the new playlist')
clean_tracks_ids = [track['id'] for track in clean_tracks]
# Spotify is a dog and only lets us do it 100 tracks at a time
for i in range((len(clean_tracks_ids) // 100)+1):
    sp.playlist_add_items(new_playlist_id, clean_tracks_ids[(i*100):((i+1)*100)])
logging.info('New playlist ready! Have a look at ' + new_playlist_name)
logging.info('The following tracks were added')
for track in tracks_added:
    new_track_info = track_information(track)
    logging.info(new_track_info['name'] + ' by ' + new_track_info['artist'])
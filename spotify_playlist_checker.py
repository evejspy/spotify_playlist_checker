import os
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from difflib import SequenceMatcher

def similar(a, b):
    """Calculates similarity between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def clean_filename(name):
    """Removes special characters and normalizes filenames."""
    # Remove extensions
    name = re.sub(r'\.(mp3|flac|wav|m4a|ogg)$', '', name)
    # Remove numbers from the beginning (as in numbered playlists)
    name = re.sub(r'^\d+[\s\.\-_]+', '', name)
    # Remove additional information like "feat.", "(official video)", etc.
    name = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name)
    # Remove special characters keeping spaces
    name = re.sub(r'[^\w\s]', '', name)
    # Normalize spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def setup_spotify():
    """Sets up authentication with the Spotify API."""
    scope = "playlist-read-private"
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        redirect_uri="http://localhost:8888/callback",
        scope=scope
    ))

def get_playlist_tracks(sp, playlist_id):
    """Gets all tracks from a Spotify playlist."""
    results = sp.playlist_items(playlist_id)
    tracks = results['items']
    
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    
    # Extract song name and artist
    track_info = []
    for item in tracks:
        if item['track']:
            track = item['track']
            artist = track['artists'][0]['name']
            track_name = track['name']
            track_info.append({
                'name': track_name,
                'artist': artist,
                'full_name': f"{artist} - {track_name}",
                'spotify_id': track['id']
            })
    
    return track_info

def get_local_tracks(directory):
    """Gets all music files in a directory."""
    music_files = []
    
    valid_extensions = ['.mp3', '.flac', '.wav', '.m4a', '.ogg']
    
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_extensions:
                clean_name = clean_filename(file)
                music_files.append({
                    'filename': file,
                    'clean_name': clean_name,
                    'path': file_path
                })
    
    return music_files

def find_missing_tracks(spotify_tracks, local_tracks, similarity_threshold=0.75):
    """Finds songs that are in the playlist but not in the local directory."""
    missing_tracks = []
    
    for sp_track in spotify_tracks:
        found = False
        for local_track in local_tracks:
            # Check if the song name is present in the filename
            full_name = sp_track['full_name']
            track_name = sp_track['name']
            artist_name = sp_track['artist']
            
            # Check various possible name variations
            variations = [
                full_name,  # Artist - Name
                track_name,  # Just the song name
                f"{track_name} - {artist_name}",  # Name - Artist
            ]
            
            for variation in variations:
                if (similar(variation, local_track['clean_name']) > similarity_threshold or
                    local_track['clean_name'].find(clean_filename(track_name)) >= 0):
                    found = True
                    break
            
            if found:
                break
        
        if not found:
            missing_tracks.append(sp_track)
    
    return missing_tracks

def main():
    # Get the Spotify playlist ID (last part of the playlist URL)
    playlist_id = input("Enter the Spotify playlist ID (e.g., 37i9dQZF1DZ06evO45P0Eo): ")
    
    # Path to the folder with downloaded music
    music_dir = input("Enter the path to your downloaded music folder: ")
    
    # Setup Spotify connection
    print("Setting up Spotify connection...")
    try:
        sp = setup_spotify()
    except Exception as e:
        print(f"Error connecting to Spotify: {e}")
        print("Check your credentials and try again.")
        return
    
    # Get playlist tracks
    print("Getting playlist tracks...")
    try:
        playlist_tracks = get_playlist_tracks(sp, playlist_id)
        print(f"Found {len(playlist_tracks)} songs in the playlist.")
    except Exception as e:
        print(f"Error getting playlist: {e}")
        return
    
    # Read local files
    print("Reading local files...")
    try:
        local_files = get_local_tracks(music_dir)
        print(f"Found {len(local_files)} music files locally.")
    except Exception as e:
        print(f"Error reading local files: {e}")
        return
    
    # Find missing songs
    print("Comparing lists...")
    missing = find_missing_tracks(playlist_tracks, local_files)
    
    # Display results
    if missing:
        print(f"\n{len(missing)} songs need to be downloaded:")
        for i, track in enumerate(missing, 1):
            print(f"{i}. {track['artist']} - {track['name']}")
        
        # Save results to file
        with open("missing_songs.txt", "w", encoding="utf-8") as f:
            f.write(f"Total missing songs: {len(missing)}\n\n")
            for i, track in enumerate(missing, 1):
                f.write(f"{i}. {track['artist']} - {track['name']}\n")
        
        print("\nList saved to 'missing_songs.txt'")
    else:
        print("\nCongratulations! You've already downloaded all songs from the playlist.")

if __name__ == "__main__":
    main()
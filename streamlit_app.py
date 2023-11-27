import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from collections import Counter
import json
import webbrowser
import time
import threading
from dotenv import load_dotenv

OPEN_AI_API_KEY = st.secrets["OPEN_AI_API_KEY"]
SPOTIFY_CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]

# Initial setup: Logo and title
def setup_page():
    st.set_page_config(layout="wide")
    logo_path = 'melodymap_logo.png'
    st.image(logo_path, width=180)  # Adjust width as needed
    st.title('MelodyMap')


# Function to handle the OAuth flow and token retrieval
def get_access_token(auth_code, redirect_uri):
    token_url = "https://accounts.spotify.com/api/token"
    client_id = SPOTIFY_CLIENT_ID
    client_secret = SPOTIFY_CLIENT_SECRET

    auth_response = requests.post(token_url, data={
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': redirect_uri
    }, auth=HTTPBasicAuth(client_id, client_secret))

    if auth_response.status_code == 200:
        return auth_response.json().get('access_token')
    else:
        st.write("Please authenticate via Spotify.")
        return None

# Function to fetch the last 50 songs
def fetch_songs(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get("https://api.spotify.com/v1/me/player/recently-played?limit=50", headers=headers)

    if response.status_code == 200:
            last_played_tracks = response.json()['items']

            track_data = []
            for track in last_played_tracks:
                track_name = track['track']['name']
                artists = ', '.join(artist['name'] for artist in track['track']['artists'])
                album_id = track['track']['album']['id']
                popularity = track['track']['popularity']  # Get track popularity


                # Fetch album details for the release date and album name
                album_response = requests.get(f"https://api.spotify.com/v1/albums/{album_id}", headers=headers)
                if album_response.status_code == 200:
                    album_data = album_response.json()
                    release_date = album_data['release_date']
                    album_name = album_data['name']  # Extract album name
                    # Extract only the year part
                    release_year = release_date.split("-")[0]  # Assumes format is "YYYY-MM-DD" or just "YYYY"
                else:
                    release_year = "Unknown"
                    album_name = "Unknown"

                #Fetch genre from artist
                artist_id = track['track']['artists'][0]['id']  # Provdes genre of the first artist
                artist_response = requests.get(f"https://api.spotify.com/v1/artists/{artist_id}", headers=headers)
                if artist_response.status_code == 200:
                    artist_data = artist_response.json()
                    genres = artist_data['genres']  # List of genres
                else:
                    genres = ["Unknown"]

                track_data.append({
                    'Name': track_name, 
                    'Artist': artists, 
                    'Album': album_name, 
                    'Release Year': release_year, 
                    'Raw Popularity': popularity, 
                    'Genre': genres
                })
            return pd.DataFrame(track_data)
    else:
        st.error("Failed to fetch tracks.")
        return None

# Function to create and display visualizations
def display_visualizations(df_tracks):

            # Flatten the list of genres from all tracks and count occurrences
            all_genres = [genre for genres in df_tracks['Genre'] for genre in genres]
            genre_counts = Counter(all_genres)

            # Convert 'Release Year' from string to integer
            df_tracks['Release Year'] = df_tracks['Release Year'].astype(int)

            # Square the popularity to make difference more visible
            df_tracks['Popularity'] = df_tracks['Raw Popularity'] ** 2


            # Radar Chart
            # Data for radar chart
            categories = list(genre_counts.keys())
            values = list(genre_counts.values())

            # Create radar chart
            fig_radar = go.Figure(data=go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself'
            ))

            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, max(values)]
                    )),
                showlegend=False
            )

            # Create Treemap
            fig_treemap = px.treemap(
                names=categories,
                parents=[""] * len(categories),
                values=values,
                title='Genre Distribution'
            )

            # Set a fixed height for the treemap
            fig_treemap.update_layout(height=850)  # Set the height as needed


            # Create scatterplot
            fig = px.scatter(df_tracks, x='Release Year', y=[0]*len(df_tracks), 
                 size='Popularity',
                 hover_name='Name', 
                 labels={"y": ""})

            fig.update_traces(marker=dict(size=10),
                            selector=dict(mode='markers+text'))

            fig.update_layout(xaxis_title="Release Year",
                            yaxis_title="",
                            yaxis_showgrid=False, yaxis_zeroline=False,
                            yaxis_visible=False,  # Hides the y-axis
                            showlegend=False)

            fig.update_xaxes(range=[df_tracks['Release Year'].min() - 1, 
                                    df_tracks['Release Year'].max() + 1])
            
            fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))


            # Display the three charts
            st.title('Your musical timeline')
            st.plotly_chart(fig, use_container_width=True)
            st.write("")
            st.markdown("---")
            
            # st.plotly_chart(fig_radar, use_container_width=True) # Not showing radar atm
            
            st.title('Your favourite genres')
            st.plotly_chart(fig_treemap, use_container_width=True)
            st.write("")
            st.markdown("---")
            
            # Data for plots
            st.write("Data for plots")
            st.write(st.session_state['df_tracks'])

def chatgpt_poem(songs):
    api_key = OPEN_AI_API_KEY 
    endpoint = "https://api.openai.com/v1/chat/completions"  # Chat API endpoint
    user_message = "Please write me a short poem of less than 12 lines, based on these recent songs I've listened to:\n" + "\n".join(
        
    ) + "\nDo not respond with anything else other than the poem."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        "max_tokens": 150,
        "temperature": 0.7,
        "top_p": 1,
        "frequency_penalty": 0.5,
        "presence_penalty": 0
    }

    response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    if response.status_code != 200:
        st.error(f"Failed to authenticate with ChatGPT API. Status Code: {response.status_code}, Response: {response.text}")
        return None

    return response.json()

def chatgpt_travel_destination(songs):
    api_key = OPEN_AI_API_KEY 
    endpoint = "https://api.openai.com/v1/chat/completions"  # Chat API endpoint
    user_message = "Please suggest an unusual travel destination for me, based on these recent songs I've listened to:\n" + "\n".join(songs) + "\nRespond with a location (city/town/region) and the country it's in. Suggest unusual destinations that are not incredibly popular, but are not unheard of. Provide some brief reasoning as to why it would be suitable given the songs I've listened to."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        "max_tokens": 150,
        "temperature": 0.7,
        "top_p": 1,
        "frequency_penalty": 0.5,
        "presence_penalty": 0
    }

    response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    if response.status_code != 200:
        st.error(f"Failed to authenticate with ChatGPT API. Status Code: {response.status_code}, Response: {response.text}")
        return None

    return response.json()

def chatgpt_historical_context(songs):
    api_key = OPEN_AI_API_KEY
    endpoint = "https://api.openai.com/v1/chat/completions"  # Chat API endpoint
    user_message = "Please give me some historical context about these recent songs I've listened to:\n" + "\n".join(songs) + "\nRespond with a quick overview of the songs, and then a 3 specific pieces of historical context, or interesting historical facts about the songs, such as what they reference, what they were inspired by, or how they were made"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        "max_tokens": 150,
        "temperature": 0.7,
        "top_p": 1,
        "frequency_penalty": 0.5,
        "presence_penalty": 0
    }

    response = requests.post(endpoint, headers=headers, data=json.dumps(data))

    if response.status_code != 200:
        st.error(f"Failed to authenticate with ChatGPT API. Status Code: {response.status_code}, Response: {response.text}")
        return None

    return response.json()

def main():
    setup_page()

    # Define redirect_uri at the top of your main function
    redirect_uri = "http://localhost:8501"

    # Initialize session state variables
    if 'auth_code' not in st.session_state:
        st.session_state['auth_code'] = None
    if 'data_fetched' not in st.session_state:
        st.session_state['data_fetched'] = False
    if 'df_tracks' not in st.session_state:  # Initialize df_tracks in session state
        st.session_state['df_tracks'] = None
    if 'access_token' not in st.session_state:  # Initialize access_token in session state
        st.session_state['access_token'] = None

    # Step 1: Authorize Spotify
    if not st.session_state['auth_code']:
        auth_url = f"https://accounts.spotify.com/authorize?client_id={SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={redirect_uri}&scope=user-read-recently-played"
        st.markdown(f"[Authorize Spotify!]({auth_url})", unsafe_allow_html=True)

    # Step 2: Fetch Spotify Data
    query_params = st.experimental_get_query_params()
    auth_code = query_params.get("code", [None])[0]
    if auth_code:
        st.session_state['auth_code'] = auth_code

    if st.session_state['auth_code'] and not st.session_state['data_fetched']:
        if st.button('Let\'s go!'):
            with st.spinner('Fetching your data...'):
                st.session_state['access_token'] = get_access_token(st.session_state['auth_code'], redirect_uri)
                if st.session_state['access_token']:
                    st.session_state['df_tracks'] = fetch_songs(st.session_state['access_token'])
                    if st.session_state['df_tracks'] is not None:
                        # Call the function with session state variable
                        display_visualizations(st.session_state['df_tracks'])
                        st.session_state['data_fetched'] = True

    st.write("")
    st.markdown("---")

    st.title('Explore')

    # Poem Generation Button
    if st.button("Write me a poem"):
        if st.session_state.get('df_tracks') is not None:
            with st.spinner("Retrieving your poem..."):
                songs_with_artists = st.session_state['df_tracks'].apply(lambda row: f"{row['Name']} by {row['Artist']}", axis=1).tolist()
                poem_response = chatgpt_poem(songs_with_artists)
                poem_text = poem_response.get('choices', [{}])[0].get('message', {}).get('content', '')

            if poem_text:
                # Replace newline characters with HTML line breaks for correct rendering
                formatted_poem = poem_text.replace("\n", "<br>")
                st.markdown(f"<p style='font-family:serif; color:PaleGoldenRod; font-size: 20px;'>{formatted_poem}</p>", unsafe_allow_html=True)
    
    # Travel Destination Button
    if st.button("Suggest a travel destination"):
        if st.session_state.get('df_tracks') is not None:  # Check if df_tracks exists
            with st.spinner("Retrieving your travel destination..."):
                songs_with_artists = st.session_state['df_tracks'].apply(lambda row: f"{row['Name']} by {row['Artist']}", axis=1).tolist()
                travel_response = chatgpt_travel_destination(songs_with_artists)
                travel_text = travel_response.get('choices', [{}])[0].get('message', {}).get('content', '')

            if travel_text:
                # Replace newline characters with HTML line breaks for correct rendering
                formatted_travel = travel_text.replace("\n", "<br>")
                st.markdown(f"<p style='font-family:serif; color:PaleGoldenRod; font-size: 20px;'>{formatted_travel}</p>", unsafe_allow_html=True)

    # Historical Context Button
    if st.button("Give me some history"):
        if st.session_state.get('df_tracks') is not None:  # Check if df_tracks exists
            with st.spinner("Retrieving historical context..."):
                songs_with_artists = st.session_state['df_tracks'].apply(lambda row: f"{row['Name']} by {row['Artist']}", axis=1).tolist()
                history_response = chatgpt_historical_context(songs_with_artists)
                history_text = history_response.get('choices', [{}])[0].get('message', {}).get('content', '')

            if history_text:
                # Replace newline characters with HTML line breaks for correct rendering
                formatted_history = history_text.replace("\n", "<br>")
                st.markdown(f"<p style='font-family:serif; color:PaleGoldenRod; font-size: 20px;'>{formatted_history}</p>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
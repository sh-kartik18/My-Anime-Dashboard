import requests
import json
import csv
import os

# =========================
# CONFIG
# =========================
CLIENT_ID = ""  
CLIENT_SECRET = ""  # Replace with your AniList client_secret
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKENS_FILE = os.path.join(BASE_DIR, "tokens.json")
CSV_FILE = os.path.join(BASE_DIR, "anilist_list.csv")
USERNAME = ""  # Your AniList username

# =========================
# HELPER FUNCTIONS
# =========================
def load_tokens():
    if os.path.exists(TOKENS_FILE):
      with open(TOKENS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data if isinstance(data, dict) else None
    return None

def save_tokens(tokens):
  with open(TOKENS_FILE, "w", encoding="utf-8") as f:
    json.dump(tokens, f, indent=2)

def refresh_access_token():
    tokens = load_tokens()
    refresh_token = (tokens or {}).get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token.strip():
      raise Exception(
      f"No refresh_token found in {TOKENS_FILE}. Run auth script first."
    )

    url = "https://anilist.co/api/v2/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    "refresh_token": refresh_token
    }
    r = requests.post(url, json=data)
    if r.status_code != 200:
        raise Exception(f"Failed to refresh token: {r.text}")

    new_tokens = r.json()
    save_tokens(new_tokens)
    return new_tokens["access_token"]

def get_user_id(username, access_token):
    url = "https://graphql.anilist.co"
    query = """
    query ($name: String) {
      User(name: $name) {
        id
      }
    }
    """
    variables = {"name": username}
    r = requests.post(url, json={"query": query, "variables": variables},
                      headers={"Authorization": f"Bearer {access_token}"})
    data = r.json()
    return data["data"]["User"]["id"]

def fetch_anime_list(username, access_token):
    user_id = get_user_id(username, access_token)

    url = "https://graphql.anilist.co"
    query = """
    query ($userId: Int) {
      MediaListCollection(userId: $userId, type: ANIME) {
        lists {
          name
          entries {
            score
            status
            progress
            repeat
            media {
              id
              title {
                romaji
                english
              }
              episodes
              format
              status
              genres
              averageScore
              popularity
              startDate { year month day }
              endDate { year month day }
              coverImage {
                large
              }
              studios {
                  edges {
                  isMain
                    node {
                      name
                      }
                  }
              }
            }
          }
        }
      }
    }
    """

    variables = {"userId": user_id}
    r = requests.post(url, json={"query": query, "variables": variables},
                      headers={"Authorization": f"Bearer {access_token}"})
    data = r.json()

    if not data.get("data") or not data["data"].get("MediaListCollection"):
        raise Exception(f"Failed to fetch anime list: {data}")

    # Flatten into rows
    rows = []
    for lst in data["data"]["MediaListCollection"]["lists"]:
      for entry in lst["entries"]:
          media = entry["media"]

          main_studio = None

          for edge in media["studios"]["edges"]:
              if edge["isMain"]:
                  main_studio = edge["node"]["name"]
                  break

          rows.append({
              "list_name": lst["name"],
              "title_romaji": media["title"]["romaji"],
              "title_english": media["title"]["english"],
              "episodes": media["episodes"],
              "format": media["format"],
              "media_status": media["status"],
              "genres": ", ".join(media["genres"]),
              "average_score": media["averageScore"],
              "popularity": media["popularity"],
              "score": entry["score"],
              "watch_status": entry["status"],
              "progress": entry["progress"],
              "studio": main_studio,
              "repeat_count": entry["repeat"],
              "start_date": f"{media['startDate']['year']}-{media['startDate']['month']}-{media['startDate']['day']}",
              "end_date": f"{media['endDate']['year']}-{media['endDate']['month']}-{media['endDate']['day']}",
              "cover_image": media["coverImage"]["large"]
          })
    return rows

# =========================
# MAIN SCRIPT
# =========================
if __name__ == "__main__":
    access_token = refresh_access_token()
    anime_list = fetch_anime_list(USERNAME, access_token)

    # Save to CSV
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as csvfile:
          writer = csv.DictWriter(csvfile, fieldnames=anime_list[0].keys())
          writer.writeheader()
          writer.writerows(anime_list)

    print(f"Saved {len(anime_list)} entries to {CSV_FILE}")

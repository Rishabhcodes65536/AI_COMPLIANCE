from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route('/fetch-content', methods=['GET'])
def fetch_all_metadata():
    url = "https://www.revisor.mn.gov/statutes/cite/245D/full"  # Target URL

    try:
        response = requests.get(url)

        # Extract metadata
        metadata = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "cookies": requests.utils.dict_from_cookiejar(response.cookies),
            "url": response.url,
            "redirected": response.is_redirect,
            "encoding": response.encoding,
            "elapsed_time": response.elapsed.total_seconds(),
            "history": [r.url for r in response.history]  # URLs if there were redirects
        }

        # Print metadata to console
        print("Response Metadata (excluding body):")
        for key, value in metadata.items():
            print(f"{key}: {value}")

        # Return metadata as JSON
        return jsonify({
            "status": "success",
            "metadata": metadata
        }), 200

    except requests.exceptions.RequestException as e:
        print(f"Error fetching content: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

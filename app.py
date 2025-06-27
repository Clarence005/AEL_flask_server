from flask import Flask, send_from_directory, request, Response
import os
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  

@app.route('/stream/<path:filename>')
def serve_static(filename):
    path = os.path.abspath('lionking_hls')
    return send_from_directory(path, filename)

@app.route('/ads/<path:filename>')
def serve_ads(filename):
    path = os.path.abspath('ad_hls')
    return send_from_directory(path, filename)

@app.route('/video.m3u8')
def get_video_playlist():
    show_ad = request.args.get('showAd', 'false') == 'true'
    lion_path = os.path.join('lionking_hls', 'lionking.m3u8')
    ad_path = os.path.join('ad_hls', 'ad.m3u8')

    try:
        with open(lion_path, 'r') as f:
            lion_content = f.read()
        with open(ad_path, 'r') as f:
            ad_content = f.read()
    except Exception as e:
        return Response('Error reading HLS files.', status=500)

    lion_lines = [line.strip() for line in lion_content.splitlines() if line.strip() and not line.startswith('#EXT-X-ENDLIST')]

    lion_headers = [line for line in lion_lines if any(line.startswith(h) for h in [
        '#EXTM3U', '#EXT-X-VERSION', '#EXT-X-TARGETDURATION', '#EXT-X-MEDIA-SEQUENCE', '#EXT-X-PLAYLIST-TYPE'
    ])]

    lion_segments = [line for line in lion_lines if line not in lion_headers]

    def add_static_prefix(lines):
        return [f"/stream/{line}" if line.endswith('.ts') else line for line in lines]

    def add_ads_prefix(lines):
        return [f"/ads/{line}" if line.endswith('.ts') else line for line in lines]

    lion_segments_with_static = add_static_prefix(lion_segments)
    print('\n'.join(lion_segments_with_static[:3]))

    ad_lines = [line.strip() for line in ad_content.splitlines()
                if line.strip() and not any(line.startswith(h) for h in [
                    '#EXTM3U', '#EXT-X-VERSION', '#EXT-X-TARGETDURATION',
                    '#EXT-X-MEDIA-SEQUENCE', '#EXT-X-PLAYLIST-TYPE', '#EXT-X-ENDLIST'
                ])]

    ad_lines_with_prefix = add_ads_prefix(ad_lines)

    if not show_ad:
        final_playlist = '\n'.join(lion_headers + lion_segments_with_static + ['#EXT-X-ENDLIST'])
        return Response(final_playlist, mimetype='application/vnd.apple.mpegurl')

    ad_durations = [float(line.replace('#EXTINF:', '').replace(',', ''))
                    for line in ad_content.splitlines()
                    if line.strip().startswith('#EXTINF:')]

    ad_duration_ms = round(sum(ad_durations) * 1000)

    combined = '\n'.join([
        *lion_headers,
        lion_segments_with_static[0],
        lion_segments_with_static[1],
        '#EXT-X-DISCONTINUITY',
        *ad_lines_with_prefix,
        '#EXT-X-DISCONTINUITY',
        *lion_segments_with_static[2:],
        '#EXT-X-ENDLIST'
    ])

    response = Response(combined, mimetype='application/vnd.apple.mpegurl')
    response.headers['X-Ad-Duration'] = str(ad_duration_ms)
    return response


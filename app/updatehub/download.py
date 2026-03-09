import os
import requests as http_requests
from flask import request, jsonify, send_from_directory, redirect, abort, Response, stream_with_context
from app.updatehub import updatehub
from app.models import AppVersion
from app.utils.validators import is_valid_app_name, is_valid_version, is_valid_platform
import config


@updatehub.route('/api/<app_name>/download', methods=['GET'])
def download_update(app_name):
    """
    下载指定版本。
    Query: platform=windows|mac|linux  &  version=1.0.1
    行为由版本元数据中的 source 字段决定：
      - local        : 直接返回服务器本地文件
      - github       : 302 重定向到 GitHub Release 原始地址
      - github_proxy : 服务器从 GitHub 拉取后流式中转给客户端
    """
    if not is_valid_app_name(app_name):
        abort(400)

    platform = request.args.get('platform', '').lower()
    version  = request.args.get('version', '')

    if not is_valid_platform(platform):
        abort(400)
    if not is_valid_version(version):
        abort(400)

    row = AppVersion.query.filter_by(
        app_name=app_name, version=version, platform=platform
    ).first()
    if not row:
        abort(404)

    if row.source == 'github':
        # 直接重定向，由客户端自行从 GitHub 下载
        if not row.github_url:
            abort(404)
        return redirect(row.github_url, code=302)

    if row.source == 'github_proxy':
        # 服务器作为中转：从 GitHub 拉取后流式传给客户端
        if not row.github_url:
            abort(404)
        github_url = row.github_url
        filename   = github_url.split('/')[-1] or f"{app_name}-{version}-{platform}"

        def generate():
            with http_requests.get(github_url, stream=True, timeout=30) as r:
                if r.status_code != 200:
                    abort(502)
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        yield chunk

        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type':        'application/octet-stream',
        }
        # 透传文件大小以便客户端显示进度条
        try:
            probe = http_requests.head(github_url, timeout=10, allow_redirects=True)
            content_length = probe.headers.get('Content-Length')
            if content_length:
                headers['Content-Length'] = content_length
        except Exception:
            pass
        return Response(stream_with_context(generate()), headers=headers)

    # source == 'local'
    directory = os.path.join(config.UPLOAD_FOLDER, app_name, platform)
    if not row.filename:
        return jsonify({'error': '文件记录不完整，缺少文件名'}), 404
    if not os.path.exists(os.path.join(directory, row.filename)):
        return jsonify({'error': f'文件不存在于服务器：{row.filename}，请重新上传'}), 404
    return send_from_directory(directory, row.filename, as_attachment=True)

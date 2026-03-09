"""
app/apistack/handlers.py - API 处理函数注册表。

设计说明：
    每个 API 的实际业务逻辑以普通函数的形式定义在本文件中，
    通过 @register('<api_name>') 装饰器写入内部注册表 _REGISTRY。
    views.py 中的路由层通过 get_handler(api_name) 查找并调用对应函数。
    api_name 匹配时大小写不敏感（统一转为小写后比对）。

新增 API 三步骤：
    1. 在数据库（或 seed.py）中插入对应的 ApiEntry 记录；
    2. 在本文件末尾使用 @register('name') 定义处理函数；
    3. 处理函数直接返回 Flask Response 对象（如 jsonify(...)）。

示例：
    @register('myNewApi')
    def myNewApi():
        return jsonify({'message': 'hello'})
"""
import requests
from flask import jsonify

# 内部注册表：api_name（小写）-> 处理函数
_REGISTRY: dict = {}


def register(name: str):
    """将处理函数注册到 _REGISTRY 的装饰器。

    Args:
        name: API 名称，与数据库 ApiEntry.name 及 URL 中的 <api_name> 对应。
              注册时统一转为小写存储，查询时大小写不敏感。

    Returns:
        decorator: 返回原函数不变，仅产生注册副作用。
    """
    def decorator(fn):
        _REGISTRY[name.lower()] = fn
        return fn
    return decorator


def get_handler(name: str):
    """根据名称从注册表中查找处理函数。

    Args:
        name: API 名称，大小写不敏感。

    Returns:
        callable | None: 对应的处理函数；若未注册则返回 None，
                         调用方应返回 501 响应。
    """
    return _REGISTRY.get(name.lower())


# ── 具体 API 处理函数 ──────────────────────────────────────────────────────────
# 在下方继续添加新的处理函数，遵循以下规范：
#   - 使用 @register('<name>') 装饰，name 与 ApiEntry.name 保持一致
#   - 函数直接返回 Flask Response（jsonify / make_response）
#   - 外部请求失败统一返回 502，参数错误返回 400

@register('bingWallpaper')
def bingWallpaper():
    """获取 Bing 首页每日壁纸的元信息。

    向 Bing HPImageArchive 接口请求当日壁纸数据（中文区），
    返回标题、版权声明、原图 URL 及日期范围。

    Returns:
        Response (200): JSON 字段说明：
            - title     (str): 壁纸标题。
            - copyright (str): 版权声明文字。
            - url       (str): 壁纸原图绝对 URL（含 Bing 域名）。
            - startdate (str): 展示开始日期，格式 YYYYMMDD。
            - enddate   (str): 展示结束日期，格式 YYYYMMDD。
        Response (502): 上游请求失败时返回 ``{"error": "<异常信息>"}``。
    """
    try:
        resp = requests.get(
            'https://www.bing.com/HPImageArchive.aspx',
            params={'format': 'js', 'idx': 0, 'n': 1, 'mkt': 'zh-CN'},
            timeout=8,
        )
        resp.raise_for_status()
        image = resp.json()['images'][0]
        return jsonify({
            'title':     image.get('title'),
            'copyright': image.get('copyright'),
            'url':       'https://www.bing.com' + image.get('url', ''),
            'startdate': image.get('startdate'),
            'enddate':   image.get('enddate'),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 502
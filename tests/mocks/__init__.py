"""
hdc 命令返回值模拟数据

用于单元测试的 mock 数据。
"""

# 设备列表
DEVICES_OUTPUT = """device_001
device_002"""

# UI 树 JSON
UI_TREE_SAMPLE = {
    "type": "Root",
    "children": [
        {
            "type": "Column",
            "children": [
                {
                    "type": "Button",
                    "text": "登录",
                    "bounds": {"left": 100, "top": 200, "right": 300, "bottom": 250}
                },
                {
                    "type": "TextInput",
                    "text": "请输入用户名",
                    "bounds": {"left": 100, "top": 300, "right": 500, "bottom": 350}
                }
            ]
        }
    ]
}

# hilog 日志样本
HILOG_SAMPLE = """01-31 10:00:00.123  1234  1234 I MyTag: Application started
01-31 10:00:01.456  1234  1234 D MyTag: Loading config
01-31 10:00:02.789  1234  1234 W MyTag: Config file not found
01-31 10:00:03.012  1234  1234 E MyTag: Failed to load config
01-31 10:00:04.345  1234  1234 F MyTag: Application crashed"""

# 包信息
PACKAGE_INFO_SAMPLE = {
    'success': True,
    'abilities': [
        {'name': 'MainAbility', 'module': 'entry', 'type': 'page'},
        {'name': 'ServiceAbility', 'module': 'entry', 'type': 'service'}
    ],
    'modules': ['entry'],
    'main_ability': {'ability_name': 'MainAbility', 'module_name': 'entry'}
}

# 窗口列表
WINDOW_LIST_SAMPLE = {
    'success': True,
    'windows': [
        {
            'window_id': 1,
            'bundle_name': 'com.example.app',
            'is_visible': True,
            'bounds': {'left': 0, 'top': 0, 'right': 1080, 'bottom': 2400}
        },
        {
            'window_id': 2,
            'bundle_name': 'com.huawei.systemui',
            'is_visible': True,
            'bounds': {'left': 0, 'top': 0, 'right': 1080, 'bottom': 100}
        }
    ]
}

# 构建结果
BUILD_RESULT_SUCCESS = {
    'success': True,
    'hap_path': '/path/to/output/entry-default-signed.hap'
}

BUILD_RESULT_FAILURE = {
    'success': False,
    'error': 'ERROR: Compilation failed\nError Message: Cannot find module'
}

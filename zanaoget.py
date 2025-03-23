import requests
import urllib3
import json
import time
import execjs
import os
import random
import sys
import re
import pickle
from datetime import datetime
from io import BytesIO
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QSpinBox, 
                            QDoubleSpinBox, QLabel, QVBoxLayout, QHBoxLayout, 
                            QWidget, QTextEdit, QProgressBar, QFileDialog, 
                            QMessageBox, QGroupBox, QFormLayout, QCheckBox,
                            QListWidget, QListWidgetItem, QDialog, QSplitter, 
                            QTabWidget, QScrollArea, QLineEdit, QGridLayout, QStatusBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QPixmap
# 替换fpdf为reportlab库
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.units import inch, cm
    HAS_REPORTLAB = True
except ImportError:
    print("无法导入reportlab库，PDF功能将不可用")
    print("请使用pip install reportlab安装")
    HAS_REPORTLAB = False

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 用户令牌
USER_TOKEN = "输入你的赞噢Token"

# CDN基础URL
CDN_BASE_URL = "https://b1.cdn.zanao.com/"

# 帖子详情对话框
class PostDetailDialog(QDialog):
    def __init__(self, post_data, parent=None):
        super().__init__(parent)
        self.post_data = post_data
        self.image_cache = {}  # 缓存已加载的图片
        self.initUI()
        
    def initUI(self):
        # 设置窗口属性
        thread_id = self.post_data.get('thread_id', 'unknown')
        title = self.post_data.get('title', '无标题')
        self.setWindowTitle(f'帖子详情 - {title} (ID: {thread_id})')
        self.resize(800, 600)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建标签页控件
        tab_widget = QTabWidget()
        
        # 创建内容标签页
        content_tab = QWidget()
        content_layout = QVBoxLayout(content_tab)
        
        # 创建信息区域的滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # 添加标题
        title_label = QLabel(title)
        title_label.setFont(QFont("", 16, QFont.Bold))
        title_label.setWordWrap(True)
        scroll_layout.addWidget(title_label)
        
        # 添加作者信息
        author = self.post_data.get('nickname', '匿名用户')
        level = self.post_data.get('user_level_title', '普通用户')
        author_label = QLabel(f'作者: {author} ({level})')
        scroll_layout.addWidget(author_label)
        
        # 添加发布时间
        post_time = self.post_data.get('post_time', '未知时间')
        p_time_stamp = int(self.post_data.get('p_time', 0))
        if p_time_stamp > 0:
            p_time_str = datetime.fromtimestamp(p_time_stamp).strftime('%Y-%m-%d %H:%M:%S')
            time_label = QLabel(f'发布时间: {post_time} ({p_time_str})')
        else:
            time_label = QLabel(f'发布时间: {post_time}')
        scroll_layout.addWidget(time_label)
        
        # 添加帖子内容
        scroll_layout.addWidget(QLabel("内容:"))
        content = self.post_data.get('content', '')
        content_text = QTextEdit()
        content_text.setReadOnly(True)
        content_text.setText(content)
        content_text.setMinimumHeight(100)
        scroll_layout.addWidget(content_text)
        
        # 添加图片区域
        img_paths = self.post_data.get('img_paths', [])
        if img_paths:
            scroll_layout.addWidget(QLabel(f"图片 ({len(img_paths)}张):"))
            
            # 创建图片容器
            img_container = QWidget()
            img_layout = QVBoxLayout(img_container)
            
            for i, img_path in enumerate(img_paths):
                # 处理图片URL
                if img_path.startswith('//'):
                    img_url = 'https:' + img_path
                elif img_path.startswith('http'):
                    img_url = img_path
                else:
                    img_url = CDN_BASE_URL + img_path
                
                # 创建图片标签
                img_label = QLabel(f"图片 {i+1}: {os.path.basename(img_path)}")
                img_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                img_layout.addWidget(img_label)
                
                # 尝试加载本地图片
                thread_id = self.post_data.get('thread_id', 'unknown')
                local_img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "images", f"thread_{thread_id}")
                
                if os.path.exists(local_img_dir):
                    # 查找可能的图片文件
                    for file_name in os.listdir(local_img_dir):
                        if file_name.startswith(f"{i+1}_"):
                            local_path = os.path.join(local_img_dir, file_name)
                            try:
                                pixmap = QPixmap(local_path)
                                if not pixmap.isNull():
                                    # 缩放图片，最大宽度为500
                                    if pixmap.width() > 500:
                                        pixmap = pixmap.scaledToWidth(500, Qt.SmoothTransformation)
                                    img_view = QLabel()
                                    img_view.setPixmap(pixmap)
                                    img_layout.addWidget(img_view)
                                    break
                            except Exception as e:
                                print(f"加载图片失败: {e}")
                
                img_layout.addSpacing(10)
            
            scroll_layout.addWidget(img_container)
        
        # 添加评论区域
        comments = self.post_data.get('comment_list', [])
        if comments:
            scroll_layout.addWidget(QLabel(f"评论 ({len(comments)}条):"))
            
            # 创建评论容器
            comment_container = QWidget()
            comment_layout = QVBoxLayout(comment_container)
            
            for comment in comments:
                comment_author = comment.get('nickname', '匿名用户')
                comment_content = comment.get('content', '')
                
                # 创建评论框
                comment_box = QGroupBox()
                comment_box_layout = QVBoxLayout(comment_box)
                
                # 添加评论作者和内容
                comment_text = QLabel(f"{comment_author}: {comment_content}")
                comment_text.setWordWrap(True)
                comment_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
                comment_box_layout.addWidget(comment_text)
                
                # 添加回复
                replies = comment.get('reply_list', [])
                for reply in replies:
                    reply_author = reply.get('nickname', '匿名用户')
                    reply_to = reply.get('reply_nickname', '匿名用户')
                    reply_content = reply.get('content', '')
                    
                    # 创建回复标签
                    reply_text = QLabel(f"↪ {reply_author} 回复 {reply_to}: {reply_content}")
                    reply_text.setWordWrap(True)
                    reply_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    reply_text.setContentsMargins(20, 0, 0, 0)
                    comment_box_layout.addWidget(reply_text)
                
                comment_layout.addWidget(comment_box)
            
            scroll_layout.addWidget(comment_container)
        
        # 设置滚动区域内容
        scroll_area.setWidget(scroll_content)
        content_layout.addWidget(scroll_area)
        
        # 添加标签页
        tab_widget.addTab(content_tab, "帖子内容")
        
        # 添加标签页到主布局
        main_layout.addWidget(tab_widget)
        
        # 添加底部按钮
        button_layout = QHBoxLayout()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        button_layout.addStretch(1)
        button_layout.addWidget(close_btn)
        main_layout.addLayout(button_layout)

# 帖子预览列表窗口
class PostListWindow(QMainWindow):
    def __init__(self, posts_data, parent=None):
        super().__init__(parent)
        self.posts_data = posts_data
        self.filtered_posts = []
        self.initUI()
        
    def initUI(self):
        # 设置窗口属性
        self.setWindowTitle('帖子预览列表')
        self.resize(600, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # 添加搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索标题和内容")
        self.search_input.textChanged.connect(self.filter_posts)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)
        
        # 创建列表部件
        self.post_list = QListWidget()
        self.post_list.itemDoubleClicked.connect(self.show_post_detail)
        
        # 加载所有帖子
        self.load_posts()
        
        main_layout.addWidget(self.post_list)
        
        # 添加底部按钮
        button_layout = QHBoxLayout()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self.refresh_list)
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch(1)
        button_layout.addWidget(close_btn)
        main_layout.addLayout(button_layout)
        
        # 设置中央部件
        self.setCentralWidget(central_widget)
    
    def load_posts(self):
        """加载所有帖子到列表中"""
        self.post_list.clear()
        if 'data' in self.posts_data and 'list' in self.posts_data['data']:
            self.filtered_posts = self.posts_data['data']['list']
            self.update_list_display()
    
    def update_list_display(self):
        """更新列表显示"""
        self.post_list.clear()
        for post in self.filtered_posts:
            thread_id = post.get('thread_id', 'unknown')
            title = post.get('title', '无标题')
            author = post.get('nickname', '匿名用户')
            post_time = post.get('post_time', '未知时间')
            
            # 创建列表项
            item = QListWidgetItem()
            
            # 设置列表项文本
            item_text = f"{title}\n作者: {author} | 发布时间: {post_time}"
            item.setText(item_text)
            
            # 设置列表项数据
            item.setData(Qt.UserRole, post)
            
            # 设置列表项大小提示
            item.setSizeHint(QSize(0, 60))
            
            # 添加到列表
            self.post_list.addItem(item)
        
        # 显示结果数量
        total_count = len(self.posts_data['data']['list']) if 'data' in self.posts_data and 'list' in self.posts_data['data'] else 0
        filtered_count = len(self.filtered_posts)
        self.setWindowTitle(f'帖子预览列表 - 显示 {filtered_count}/{total_count} 条')
        
    def filter_posts(self):
        """根据搜索关键词过滤帖子"""
        keyword = self.search_input.text().lower().strip()
        
        if not keyword:
            # 如果搜索框为空，显示所有帖子
            if 'data' in self.posts_data and 'list' in self.posts_data['data']:
                self.filtered_posts = self.posts_data['data']['list']
        else:
            # 否则，根据关键词过滤帖子
            if 'data' in self.posts_data and 'list' in self.posts_data['data']:
                self.filtered_posts = []
                for post in self.posts_data['data']['list']:
                    title = post.get('title', '').lower()
                    content = post.get('content', '').lower()
                    author = post.get('nickname', '').lower()
                    
                    if (keyword in title) or (keyword in content) or (keyword in author):
                        self.filtered_posts.append(post)
        
        # 更新列表显示
        self.update_list_display()
        
    def show_post_detail(self, item):
        """显示帖子详细信息对话框"""
        post_data = item.data(Qt.UserRole)
        if post_data:
            detail_dialog = PostDetailDialog(post_data, self)
            detail_dialog.exec_()
            
    def refresh_list(self):
        """刷新帖子列表"""
        self.search_input.clear()  # 清空搜索框
        self.load_posts()  # 重新加载所有帖子

# 工作线程类，用于在后台执行爬虫任务
class FetchWorker(QThread):
    # 定义信号
    update_progress = pyqtSignal(int, int)  # 当前页数，总页数
    update_log = pyqtSignal(str)  # 日志信息
    finished = pyqtSignal()  # 完成信号
    error = pyqtSignal(str)  # 错误信号
    image_downloaded = pyqtSignal(str)  # 图片下载完成信号

    def __init__(self, headers, page_count, delay, max_retries, download_images=True, image_dir=None):
        super().__init__()
        self.headers = headers
        self.page_count = page_count
        self.delay = delay
        self.max_retries = max_retries
        self.download_images = download_images
        self.image_dir = image_dir
        self.is_running = True
        self.all_data = None  # 存储所有获取的数据
        self.downloaded_images = []  # 存储下载的图片路径

    def run(self):
        try:
            result = self.fetch_zanao_data(
                self.headers, 
                timestamp=0, 
                page_count=self.page_count,
                delay=self.delay,
                max_retries=self.max_retries
            )
            if self.is_running:  # 检查是否被中断
                self.all_data = result
                self.finished.emit()
        except Exception as e:
            self.error.emit(f"爬取过程中出错: {str(e)}")

    def stop(self):
        self.is_running = False
        self.terminate()
        self.wait()

    def fetch_zanao_data(self, headers, timestamp=None, page_count=1, delay=2, max_retries=3):
        """获取赞噢平台的数据。"""
        if timestamp is None:
            timestamp = 0  # 从最新的帖子开始
        
        all_data = None
        current_timestamp = timestamp
        
        for page in range(page_count):
            if not self.is_running:
                break
                
            retries = 0
            success = False
            
            while not success and retries <= max_retries and self.is_running:
                try:
                    if retries > 0:
                        # 重试时增加延迟
                        retry_delay = delay * (1 + retries)
                        self.update_log.emit(f"第 {retries} 次重试，等待 {retry_delay} 秒...")
                        time.sleep(retry_delay)
                    
                    self.update_log.emit(f"正在获取第 {page+1} 页数据，from_time={current_timestamp}")
                    self.update_progress.emit(page+1, page_count)
                    
                    data = 'from_time=' + str(current_timestamp) + '&with_comment=true&with_reply=true'
                    
                    response = requests.post(
                        'https://api.x.zanao.com/thread/v2/list',
                        headers=headers,
                        data=data,
                        params=get_params(current_timestamp),
                        verify=False,  # 跳过证书验证
                        timeout=15  # 增加超时时间
                    )
                    response.raise_for_status()
                    
                    page_data = response.json()
                    success = True
                    
                    # 第一页时初始化结果
                    if all_data is None:
                        all_data = page_data
                    # 后续页面，将帖子列表合并
                    elif 'data' in page_data and 'list' in page_data['data'] and len(page_data['data']['list']) > 0:
                        all_data['data']['list'].extend(page_data['data']['list'])
                    else:
                        self.update_log.emit(f"第 {page+1} 页没有更多数据，停止获取")
                        break
                    
                    # 下载当前页面的图片
                    if self.download_images and 'data' in page_data and 'list' in page_data['data']:
                        self.download_page_images(page_data['data']['list'])
                        
                    # 获取最后一条帖子的时间戳作为下一页的起始时间
                    if 'data' in page_data and 'list' in page_data['data'] and len(page_data['data']['list']) > 0:
                        last_post = page_data['data']['list'][-1]
                        current_timestamp = int(last_post.get('p_time', 0))
                        
                        # 如果没有更多数据，退出循环
                        if len(page_data['data']['list']) < 10:  # 假设每页10条数据
                            self.update_log.emit(f"数据不足一页，停止获取")
                            break
                    else:
                        break
                        
                    # 添加随机延迟，避免请求过于规律
                    if page < page_count - 1 and self.is_running:
                        # 随机延迟1.5到3.5秒
                        random_delay = delay + (random.random() * 2 - 0.5)
                        self.update_log.emit(f"等待 {random_delay:.2f} 秒后获取下一页...")
                        time.sleep(random_delay)
                        
                except requests.RequestException as e:
                    retries += 1
                    self.update_log.emit(f"请求第 {page+1} 页数据失败: {e}")
                    if retries > max_retries:
                        self.update_log.emit(f"重试次数已用尽，放弃获取第 {page+1} 页数据")
                        break
                except Exception as e:
                    retries += 1
                    self.update_log.emit(f"处理第 {page+1} 页数据时出错: {e}")
                    if retries > max_retries:
                        self.update_log.emit(f"重试次数已用尽，放弃获取第 {page+1} 页数据")
                        break
        
        return all_data
        
    def download_page_images(self, posts):
        """下载帖子中的所有图片"""
        if not posts:
            return
            
        # 确保输出目录存在
        if self.image_dir:
            image_dir = self.image_dir
        else:
            image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "images")
        os.makedirs(image_dir, exist_ok=True)
        
        # 遍历所有帖子
        for post in posts:
            if not self.is_running:
                break
                
            thread_id = post.get('thread_id', 'unknown')
            img_paths = post.get('img_paths', [])
            
            if not img_paths:
                continue
                
            # 为每个帖子创建单独的文件夹
            post_img_dir = os.path.join(image_dir, f"thread_{thread_id}")
            os.makedirs(post_img_dir, exist_ok=True)
            
            # 下载帖子中的每张图片
            for idx, img_path in enumerate(img_paths):
                if not self.is_running:
                    break
                    
                # 处理图片URL
                if img_path.startswith('//'):
                    img_url = 'https:' + img_path
                elif img_path.startswith('http'):
                    img_url = img_path
                else:
                    img_url = 'https://b1.cdn.zanao.com/' + img_path
                
                # 移除URL参数部分
                clean_img_url = img_url.split('@')[0] if '@' in img_url else img_url
                
                # 提取文件名
                file_name = os.path.basename(clean_img_url)
                file_name = re.sub(r'[\\/*?:"<>|]', '_', file_name)  # 移除非法字符
                
                # 保存路径
                save_path = os.path.join(post_img_dir, f"{idx+1}_{file_name}")
                
                try:
                    # 下载图片
                    self.update_log.emit(f"正在下载图片: {file_name}")
                    
                    # 设置图片请求头，模拟浏览器行为防止403错误
                    img_headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Referer': 'https://servicewechat.com/wx3921ddb0258ff14f/60/page-frame.html',
                        'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                        'sec-ch-ua-mobile': '?0',
                        'sec-ch-ua-platform': '"Windows"',
                        'Sec-Fetch-Dest': 'image',
                        'Sec-Fetch-Mode': 'no-cors',
                        'Sec-Fetch-Site': 'cross-site',
                    }
                    
                    img_response = requests.get(clean_img_url, timeout=10, verify=False, headers=img_headers)
                    img_response.raise_for_status()
                    
                    # 检查内容类型是否为图片
                    content_type = img_response.headers.get('Content-Type', '')
                    if not content_type.startswith('image/'):
                        self.update_log.emit(f"下载的内容不是图片: {content_type}")
                        
                        # 尝试使用另一种URL格式
                        alt_url = clean_img_url
                        if '@' not in img_url:
                            # 如果URL中没有@参数，尝试添加@!sm_w300_h300
                            alt_url = clean_img_url + '@!sm_w300_h300'
                            self.update_log.emit(f"尝试替代URL: {alt_url}")
                            img_response = requests.get(alt_url, timeout=10, verify=False, headers=img_headers)
                            img_response.raise_for_status()
                    
                    # 保存图片
                    with open(save_path, 'wb') as f:
                        f.write(img_response.content)
                    
                    # 保存图片路径，用于生成PDF
                    img_info = {
                        'path': save_path,
                        'thread_id': thread_id,
                        'index': idx
                    }
                    self.downloaded_images.append(img_info)
                    
                    self.image_downloaded.emit(save_path)
                    self.update_log.emit(f"图片已保存: {save_path}")
                    
                    # 添加短暂延迟
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.update_log.emit(f"下载图片失败: {e}")
                    
                    # 尝试使用替代URL
                    try:
                        # 构建新的URL格式，包含参数
                        alt_url = clean_img_url + '@!sm_w300_h300'
                        self.update_log.emit(f"尝试使用替代URL下载: {alt_url}")
                        
                        img_headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090c2d)XWEB/11581',
                            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                            'Accept-Language': 'zh-CN,zh;q=0.9',
                            'Referer': 'https://servicewechat.com/wx3921ddb0258ff14f/60/page-frame.html',
                            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                            'sec-ch-ua-mobile': '?0',
                            'sec-ch-ua-platform': '"Windows"',
                            'Sec-Fetch-Dest': 'image',
                            'Sec-Fetch-Mode': 'no-cors',
                            'Sec-Fetch-Site': 'cross-site',
                        }
                        
                        img_response = requests.get(alt_url, timeout=10, verify=False, headers=img_headers)
                        img_response.raise_for_status()
                        
                        # 保存图片
                        with open(save_path, 'wb') as f:
                            f.write(img_response.content)
                        
                        # 保存图片路径，用于生成PDF
                        img_info = {
                            'path': save_path,
                            'thread_id': thread_id,
                            'index': idx
                        }
                        self.downloaded_images.append(img_info)
                        
                        self.image_downloaded.emit(save_path)
                        self.update_log.emit(f"使用替代URL成功下载图片: {save_path}")
                    except Exception as e2:
                        self.update_log.emit(f"使用替代URL下载图片失败: {e2}")
    
    def get_data(self):
        """获取爬取的数据"""
        if self.all_data and 'data' in self.all_data and 'list' in self.all_data['data']:
            return self.all_data['data']['list']
        return []

# 主窗口类
class ZanaoGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("赞噢数据获取工具")
        self.setGeometry(300, 300, 800, 600)
        
        # 存储已爬取的数据
        self.fetched_data = []
        self.img_save_dir = None
        self.worker = None
        self.cache_enabled = True  # 启用缓存
        
        # 设置中心小部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建设置区域
        setting_group = QGroupBox("爬取设置")
        setting_layout = QGridLayout(setting_group)
        
        # 页数设置
        page_label = QLabel("爬取页数:")
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 100)
        self.page_spin.setValue(5)
        setting_layout.addWidget(page_label, 0, 0)
        setting_layout.addWidget(self.page_spin, 0, 1)
        
        # 延迟设置
        delay_label = QLabel("请求延迟(秒):")
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.5, 10.0)
        self.delay_spin.setValue(2.0)
        self.delay_spin.setSingleStep(0.5)
        setting_layout.addWidget(delay_label, 0, 2)
        setting_layout.addWidget(self.delay_spin, 0, 3)
        
        # 重试次数设置
        retry_label = QLabel("最大重试次数:")
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(1, 10)
        self.retry_spin.setValue(3)
        setting_layout.addWidget(retry_label, 1, 0)
        setting_layout.addWidget(self.retry_spin, 1, 1)
        
        # 下载图片选项
        self.download_images_check = QCheckBox("下载图片")
        self.download_images_check.setChecked(True)
        setting_layout.addWidget(self.download_images_check, 1, 2)
        
        # 选择图片保存目录按钮
        self.img_dir_btn = QPushButton("选择图片保存目录")
        self.img_dir_btn.clicked.connect(self.select_image_directory)
        setting_layout.addWidget(self.img_dir_btn, 1, 3)
        
        # 图片保存目录路径显示
        self.img_dir_label = QLabel("默认: ./output/images")
        setting_layout.addWidget(self.img_dir_label, 2, 0, 1, 4)
        
        # 使用缓存选项
        self.cache_check = QCheckBox("使用缓存加速重复爬取")
        self.cache_check.setChecked(True)
        self.cache_check.setToolTip("启用后，相同页数的爬取结果将被缓存，再次爬取相同页数时可加快速度")
        setting_layout.addWidget(self.cache_check, 3, 0, 1, 4)
        
        # 添加设置区域到主布局
        main_layout.addWidget(setting_group)
        
        # 创建按钮区域
        button_layout = QHBoxLayout()
        
        # 开始按钮
        self.start_btn = QPushButton("开始爬取")
        self.start_btn.clicked.connect(self.start_fetch)
        button_layout.addWidget(self.start_btn)
        
        # 停止按钮
        self.stop_btn = QPushButton("停止爬取")
        self.stop_btn.clicked.connect(self.stop_fetch)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        # 备份数据按钮
        self.backup_btn = QPushButton("备份数据")
        self.backup_btn.clicked.connect(self.backup_data)
        self.backup_btn.setEnabled(False)
        button_layout.addWidget(self.backup_btn)
        
        # 恢复数据按钮
        self.restore_btn = QPushButton("恢复数据")
        self.restore_btn.clicked.connect(self.restore_data)
        button_layout.addWidget(self.restore_btn)
        
        # 保存数据按钮
        self.save_btn = QPushButton("保存数据")
        self.save_btn.clicked.connect(self.save_data)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)
        
        # 生成PDF按钮
        self.pdf_btn = QPushButton("生成PDF报告")
        self.pdf_btn.clicked.connect(self.generate_pdf)
        self.pdf_btn.setEnabled(False)
        button_layout.addWidget(self.pdf_btn)
        
        # 预览数据按钮
        self.preview_btn = QPushButton("预览数据")
        self.preview_btn.clicked.connect(self.preview_data)
        self.preview_btn.setEnabled(False)
        button_layout.addWidget(self.preview_btn)
        
        # 添加按钮区域到主布局
        main_layout.addLayout(button_layout)
        
        # 创建进度条
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)
        
        # 创建日志区域
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        # 添加日志区域到主布局
        main_layout.addWidget(log_group)
        
        # 状态条
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 初始日志
        self.log("赞噢数据获取工具已启动")
        self.log("请设置爬取参数，然后点击\"开始爬取\"按钮")
        
        # 设置图标
        # self.setWindowIcon(QIcon("icon.png"))

    def log(self, message):
        """添加日志信息到日志区域"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # 滚动到底部
        self.log_text.moveCursor(QTextCursor.End)
        
    def select_image_directory(self):
        """选择图片保存目录"""
        default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "images")
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            "选择图片保存目录", 
            default_dir,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if dir_path:
            self.img_save_dir = dir_path
            # 截断过长的路径，只显示最后40个字符
            display_path = dir_path
            if len(dir_path) > 40:
                display_path = "..." + dir_path[-37:]
            self.img_dir_label.setText(display_path)
            self.img_dir_label.setToolTip(dir_path)
            self.log(f"已设置图片保存目录: {dir_path}")
        else:
            self.img_save_dir = None
            self.img_dir_label.setText("默认")
            self.img_dir_label.setToolTip("使用默认目录")
            
    def start_fetch(self):
        """开始爬取数据"""
        try:
            # 检查网络连接
            self.check_network_connection()
            
            # 禁用开始按钮，启用停止按钮
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.save_btn.setEnabled(False)
            self.pdf_btn.setEnabled(False)
            self.preview_btn.setEnabled(False)
            
            # 清空日志
            self.log_text.clear()
            self.log("开始准备爬取数据...")
            
            # 获取参数
            page_count = self.page_spin.value()
            delay = self.delay_spin.value()
            max_retries = self.retry_spin.value()
            download_images = self.download_images_check.isChecked()
            self.cache_enabled = self.cache_check.isChecked()
            
            # 检查缓存
            cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", f"zanao_cache_p{page_count}.pkl")
            use_cache = False
            
            if self.cache_enabled and os.path.exists(cache_file):
                try:
                    with open(cache_file, 'rb') as f:
                        cache_data = pickle.load(f)
                        cache_timestamp = cache_data.get('timestamp', 0)
                        current_time = time.time()
                        # 如果缓存时间在24小时内，使用缓存
                        if current_time - cache_timestamp < 24 * 60 * 60:
                            self.log(f"发现有效缓存数据，缓存时间: {datetime.fromtimestamp(cache_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
                            
                            # 询问是否使用缓存
                            reply = QMessageBox.question(
                                self, 
                                "发现缓存数据", 
                                f"发现{datetime.fromtimestamp(cache_timestamp).strftime('%Y-%m-%d %H:%M:%S')}的缓存数据，是否使用缓存？\n使用缓存将跳过网络请求，直接加载数据。",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.Yes
                            )
                            
                            if reply == QMessageBox.Yes:
                                self.log("正在加载缓存数据...")
                                self.fetched_data = cache_data.get('data', [])
                                
                                # 更新UI
                                self.progress_bar.setValue(self.progress_bar.maximum())
                                self.start_btn.setEnabled(True)
                                self.stop_btn.setEnabled(False)
                                self.save_btn.setEnabled(True)
                                self.pdf_btn.setEnabled(True)
                                self.preview_btn.setEnabled(True)
                                self.backup_btn.setEnabled(True)
                                
                                post_count = len(self.fetched_data) if isinstance(self.fetched_data, list) else 0
                                self.log(f"缓存加载完成，共 {post_count} 条帖子")
                                self.statusBar.showMessage(f"缓存加载完成，共 {post_count} 条帖子")
                                
                                QMessageBox.information(self, "加载完成", f"缓存数据加载完成，共 {post_count} 条帖子！")
                                return
                        else:
                            self.log(f"缓存已过期 ({(current_time - cache_timestamp) / 3600:.1f} 小时前)，将重新爬取数据")
                except Exception as e:
                    self.log(f"读取缓存时出错: {str(e)}")
            
            # 确保输出目录存在
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # 设置图片目录
            if download_images:
                if self.img_save_dir:
                    image_dir = self.img_save_dir
                else:
                    image_dir = os.path.join(output_dir, "images")
                os.makedirs(image_dir, exist_ok=True)
                self.log(f"图片将保存到: {image_dir}")
            else:
                image_dir = None
            
            # 检查JS文件是否存在
            js_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "header_get.js")
            if not os.path.exists(js_file_path):
                self.log("错误：找不到header_get.js文件，无法获取请求头参数")
                QMessageBox.critical(self, "错误", "找不到header_get.js文件，无法启动爬取任务！\n请确保该文件与程序在同一目录下。")
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                return
                
            # 加载JavaScript代码
            self.log("加载JavaScript代码...")
            js_code = load_js_code(js_file_path)
            
            # 获取JavaScript执行结果
            self.log("执行JavaScript获取请求头参数...")
            js_result = get_js_result(js_code)
            
            # 获取请求头
            headers = get_headers(js_result)
            
            # 设置进度条
            self.progress_bar.setRange(0, page_count)
            self.progress_bar.setValue(0)
            
            # 创建并启动工作线程
            self.log(f"开始爬取数据，设置: 页数={page_count}, 延迟={delay}秒, 最大重试次数={max_retries}, 下载图片={download_images}")
            self.worker = FetchWorker(headers, page_count, delay, max_retries, download_images, image_dir)
            self.worker.update_progress.connect(self.update_progress)
            self.worker.update_log.connect(self.log)
            self.worker.finished.connect(self.on_fetch_finished)
            self.worker.error.connect(self.on_fetch_error)
            self.worker.image_downloaded.connect(self.on_image_downloaded)
            self.worker.start()
            
        except Exception as e:
            self.log(f"启动爬取任务时出错: {str(e)}")
            QMessageBox.critical(self, "启动失败", f"启动爬取任务时出错:\n{str(e)}")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def check_network_connection(self):
        """检查网络连接状态"""
        try:
            self.log("检查网络连接...")
            response = requests.get("https://www.baidu.com", timeout=5)
            if response.status_code == 200:
                self.log("网络连接正常")
                return True
            else:
                self.log(f"网络连接异常，状态码：{response.status_code}")
                QMessageBox.warning(self, "网络警告", f"网络连接异常，状态码：{response.status_code}\n爬取过程可能会受到影响。")
                return False
        except requests.RequestException as e:
            self.log(f"网络连接失败: {str(e)}")
            QMessageBox.critical(self, "网络错误", f"无法连接到网络，请检查网络连接后重试。\n错误信息: {str(e)}")
            raise
        
    def stop_fetch(self):
        """停止爬取数据"""
        if self.worker and self.worker.isRunning():
            self.log("正在停止爬取任务...")
            self.worker.stop()
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            
    def update_progress(self, current, total):
        """更新进度条"""
        self.progress_bar.setValue(current)
        
    def on_fetch_finished(self):
        """爬取完成时的回调"""
        self.log("爬取任务完成！")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.save_btn.setEnabled(True)
        self.pdf_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        self.backup_btn.setEnabled(True)
        
        # 获取爬取的数据
        self.fetched_data = self.worker.get_data()
        
        # 保存缓存
        if self.cache_enabled:
            try:
                cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
                os.makedirs(cache_dir, exist_ok=True)
                
                cache_file = os.path.join(cache_dir, f"zanao_cache_p{self.page_spin.value()}.pkl")
                
                cache_data = {
                    'data': self.fetched_data,
                    'timestamp': time.time(),
                    'page_count': self.page_spin.value()
                }
                
                with open(cache_file, 'wb') as f:
                    pickle.dump(cache_data, f)
                    
                self.log(f"数据已缓存到: {cache_file}")
            except Exception as e:
                self.log(f"缓存数据时出错: {str(e)}")
        
        # 更新状态栏
        self.statusBar.showMessage(f"爬取完成，共 {len(self.fetched_data)} 条帖子")
        
        # 弹出提示
        QMessageBox.information(self, "完成", f"爬取任务完成，成功获取 {len(self.fetched_data)} 条帖子数据！")
        
        # 清理工作线程
        self.worker = None
        
    def on_fetch_error(self, error_msg):
        """处理爬取过程中的错误"""
        self.log(f"错误: {error_msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
    def on_image_downloaded(self, path):
        """处理图片下载完成事件"""
        self.log(f"图片已下载: {os.path.basename(path)}")
        
    def save_data(self):
        """保存爬取结果"""
        if not self.fetched_data:
            QMessageBox.warning(self, "警告", "没有可保存的数据！")
            return
            
        try:
            # 默认输出目录
            default_output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
            os.makedirs(default_output_dir, exist_ok=True)
            
            # 让用户选择保存目录
            output_dir = QFileDialog.getExistingDirectory(
                self, 
                "选择保存目录", 
                default_output_dir,
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            # 如果用户取消了选择，则使用默认目录
            if not output_dir:
                output_dir = default_output_dir
                self.log("使用默认保存目录")
            else:
                self.log(f"已选择保存目录: {output_dir}")
            
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 创建保存选项对话框
            save_options = QMessageBox(self)
            save_options.setWindowTitle("保存选项")
            save_options.setText("请选择要保存的内容：")
            save_options.setIcon(QMessageBox.Question)
            
            # 添加按钮
            btn_json = save_options.addButton("仅保存原始JSON", QMessageBox.ActionRole)
            btn_txt = save_options.addButton("仅保存处理后文本", QMessageBox.ActionRole)
            btn_both = save_options.addButton("两者都保存", QMessageBox.ActionRole)
            btn_cancel = save_options.addButton("取消", QMessageBox.RejectRole)
            
            save_options.exec_()
            
            # 根据用户选择执行保存操作
            clicked_button = save_options.clickedButton()
            
            saved_files = []
            
            # 保存原始JSON数据
            if clicked_button in [btn_json, btn_both]:
                # 创建一个包含数据的字典
                data_to_save = {"data": {"list": self.fetched_data}}
                json_filename = os.path.join(output_dir, f"zanao_{timestamp}.json")
                if save_data(data_to_save, json_filename, is_json=True):
                    self.log(f"原始数据已保存到 {json_filename}")
                    saved_files.append(json_filename)
            
            # 处理并保存格式化数据
            if clicked_button in [btn_txt, btn_both]:
                # 创建一个包含数据的字典
                data_to_process = {"data": {"list": self.fetched_data}}
                processed = process_data(data_to_process)
                txt_filename = os.path.join(output_dir, f"zanao_data_{timestamp}.txt")
                if save_data(processed, txt_filename):
                    self.log(f"处理后的数据已保存到 {txt_filename}")
                    saved_files.append(txt_filename)
            
            # 显示保存结果
            if clicked_button != btn_cancel and saved_files:
                # 检查是否有图片被下载
                image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "images")
                has_images = os.path.exists(image_dir) and any(os.scandir(image_dir))
                
                message = f"数据已保存到:\n{chr(10).join([f'{i+1}. {f}' for i, f in enumerate(saved_files)])}"
                if has_images:
                    message += f"\n\n图片已保存到:\n{image_dir}"
                
                QMessageBox.information(self, "保存成功", message)
            
        except Exception as e:
            self.log(f"保存数据时出错: {str(e)}")
            QMessageBox.critical(self, "保存失败", f"保存数据时出错: {str(e)}")

    def generate_pdf(self):
        """创建包含帖子和图片的PDF报告"""
        if not self.fetched_data:
            QMessageBox.warning(self, "警告", "没有可保存的数据！")
            return
            
        if not HAS_REPORTLAB:
            QMessageBox.warning(self, "警告", "缺少reportlab库，无法生成PDF！\n请使用pip install reportlab安装。")
            return
            
        try:
            # 让用户选择保存位置
            default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"zanao_report_{timestamp}.pdf"
            pdf_path, _ = QFileDialog.getSaveFileName(
                self, 
                "保存PDF报告", 
                os.path.join(default_dir, default_filename),
                "PDF文件 (*.pdf)"
            )
            
            if not pdf_path:
                return
                
            self.log(f"正在生成PDF报告: {pdf_path}")
            
            # 处理字体问题
            # 使用更通用的字体处理方案
            font_path = None
            try:
                # 尝试查找系统中的中文字体
                system_fonts = [
                    # Windows中文字体位置
                    "C:/Windows/Fonts/simhei.ttf",
                    "C:/Windows/Fonts/simsun.ttc",
                    "C:/Windows/Fonts/msyh.ttc",
                    # 自定义位置
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "fonts", "simhei.ttf")
                ]
                
                for sf in system_fonts:
                    if os.path.exists(sf):
                        font_path = sf
                        self.log(f"找到系统字体: {font_path}")
                        break
                        
                # 如果未找到系统字体，下载字体
                if not font_path:
                    # 下载字体
                    out_font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "fonts", "simhei.ttf")
                    font_dir = os.path.dirname(out_font_path)
                    os.makedirs(font_dir, exist_ok=True)
                    
                    # 使用镜像站点下载字体，避免SSL问题
                    self.log("未找到系统字体，尝试下载中文字体...")
                    font_url = "https://cdn.jsdelivr.net/gh/StellarCN/scp_zh/fonts/simhei.ttf"
                    self.log(f"从 {font_url} 下载字体...")
                    font_response = requests.get(font_url, timeout=30, verify=False)
                    font_response.raise_for_status()
                    
                    with open(out_font_path, 'wb') as f:
                        f.write(font_response.content)
                    font_path = out_font_path
                    self.log(f"字体下载完成: {font_path}")
            except Exception as e:
                self.log(f"获取字体失败: {e}")
                font_path = None
            
            # 切换到使用Canvas直接绘制PDF，避免复杂的样式问题
            self.log("使用Canvas直接绘制PDF...")
            # 创建画布
            c = canvas.Canvas(pdf_path, pagesize=A4)
            
            # 页面尺寸和边距
            width, height = A4
            margin = 50
            text_width = width - 2*margin
            y = height - margin
            
            # 注册字体
            font_registered = False
            if font_path and os.path.exists(font_path):
                try:
                    # 注册中文字体
                    pdfmetrics.registerFont(TTFont('chinese', font_path))
                    font_registered = True
                    self.log("成功注册中文字体")
                except Exception as e:
                    self.log(f"注册字体失败: {e}")
            
            # 设置标题
            if font_registered:
                c.setFont('chinese', 18)
            else:
                c.setFont('Helvetica-Bold', 18)
            
            # 绘制标题
            c.drawCentredString(width/2, y, '赞噢平台数据报告')
            y -= 30
            
            # 设置正文字体
            if font_registered:
                c.setFont('chinese', 12)
            else:
                c.setFont('Helvetica', 12)
            
            # 绘制生成时间
            report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.drawString(margin, y, f'生成时间: {report_time}')
            y -= 20
            
            # 绘制帖子数量
            post_count = len(self.fetched_data)
            c.drawString(margin, y, f'帖子总数: {post_count}')
            y -= 30
            
            # 处理每个帖子
            for post_idx, post in enumerate(self.fetched_data):
                try:
                    # 检查是否需要新页面
                    if y < 100:
                        c.showPage()
                        if font_registered:
                            c.setFont('chinese', 12)
                        else:
                            c.setFont('Helvetica', 12)
                        y = height - margin
                    
                    # 绘制分隔线
                    if post_idx > 0:
                        c.line(margin, y, width-margin, y)
                        y -= 20
                    
                    # 绘制帖子ID和标题
                    thread_id = post.get('thread_id', '未知ID')
                    title = post.get('title', '无标题')
                    
                    # 设置标题字体
                    if font_registered:
                        c.setFont('chinese', 14)
                    else:
                        c.setFont('Helvetica-Bold', 14)
                        
                    c.drawString(margin, y, f'ID: {thread_id}')
                    y -= 20
                    
                    # 处理长标题，按需分行
                    title_lines = self._wrap_text(title, c, 'chinese' if font_registered else 'Helvetica-Bold', 14, text_width)
                    for line in title_lines:
                        c.drawString(margin, y, line)
                        y -= 20
                    
                    # 恢复正文字体
                    if font_registered:
                        c.setFont('chinese', 12)
                    else:
                        c.setFont('Helvetica', 12)
                    
                    # 绘制作者信息
                    author = post.get('nickname', '匿名用户')
                    level = post.get('user_level_title', '普通用户')
                    c.drawString(margin, y, f'作者: {author} ({level})')
                    y -= 20
                    
                    # 绘制发布时间
                    post_time = post.get('post_time', '未知时间')
                    p_time_stamp = int(post.get('p_time', time.time()))
                    p_time_str = datetime.fromtimestamp(p_time_stamp).strftime('%Y-%m-%d %H:%M:%S')
                    c.drawString(margin, y, f'发布时间: {post_time} ({p_time_str})')
                    y -= 20
                    
                    # 绘制帖子内容
                    content = post.get('content', '')
                    y -= 10
                    c.drawString(margin, y, '内容:')
                    y -= 20
                    
                    # 处理长内容，按需分行
                    content_lines = self._wrap_text(content, c, 'chinese' if font_registered else 'Helvetica', 12, text_width)
                    for line in content_lines:
                        c.drawString(margin, y, line)
                        y -= 20
                        # 检查是否需要新页面
                        if y < 100:
                            c.showPage()
                            if font_registered:
                                c.setFont('chinese', 12)
                            else:
                                c.setFont('Helvetica', 12)
                            y = height - margin
                    
                    y -= 10
                    
                    # 添加图片
                    img_paths = post.get('img_paths', [])
                    if img_paths:
                        c.drawString(margin, y, f'图片 ({len(img_paths)}张):')
                        y -= 30
                        
                        # 确保worker和downloaded_images存在
                        if hasattr(self, 'worker') and self.worker and hasattr(self.worker, 'downloaded_images'):
                            post_images = [img_info['path'] for img_info in self.worker.downloaded_images if img_info['thread_id'] == thread_id]
                        else:
                            # 如果worker或downloaded_images不存在（例如从缓存恢复数据时）
                            post_images = []
                            # 尝试从本地文件夹查找图片
                            thread_img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "images", f"thread_{thread_id}")
                            if os.path.exists(thread_img_dir):
                                for file_name in os.listdir(thread_img_dir):
                                    post_images.append(os.path.join(thread_img_dir, file_name))
                        
                        if post_images:
                            for img_path in post_images:
                                try:
                                    # 检查是否需要新页面 (留出足够的空间放图片)
                                    if y < 300:
                                        c.showPage()
                                        if font_registered:
                                            c.setFont('chinese', 12)
                                        else:
                                            c.setFont('Helvetica', 12)
                                        y = height - margin
                                    
                                    # 检查文件是否存在
                                    if os.path.exists(img_path):
                                        # 使用PIL检查图片格式
                                        with Image.open(img_path) as img:
                                            img_format = img.format
                                            img_width, img_height = img.size
                                            self.log(f"图片格式: {img_format}, 尺寸: {img_width}x{img_height}")
                                            
                                            # 如果不是JPEG或PNG，转换为PNG
                                            if img_format not in ['JPEG', 'PNG']:
                                                self.log("转换图片格式为PNG")
                                                converted_path = img_path + ".png"
                                                img.save(converted_path, "PNG")
                                                img_path = converted_path
                                        
                                        # 计算图片尺寸，保持宽高比
                                        display_width = 300
                                        img_ratio = img_height / img_width
                                        display_height = display_width * img_ratio
                                        
                                        # 添加图片
                                        c.drawImage(img_path, margin, y-display_height, width=display_width, height=display_height)
                                        y -= (display_height + 30)
                                except Exception as e:
                                    self.log(f"添加图片到PDF时出错: {e}")
                                    c.drawString(margin, y, f'[图片添加错误: {os.path.basename(img_path)}]')
                                    y -= 20
                        else:
                            c.drawString(margin, y, '图片未下载或下载失败')
                            y -= 20
                    
                    # 添加评论
                    comments = post.get('comment_list', [])
                    if comments:
                        y -= 10
                        c.drawString(margin, y, f'评论 ({len(comments)}条):')
                        y -= 20
                        
                        for comment in comments:
                            try:
                                # 检查是否需要新页面
                                if y < 100:
                                    c.showPage()
                                    if font_registered:
                                        c.setFont('chinese', 12)
                                    else:
                                        c.setFont('Helvetica', 12)
                                    y = height - margin
                                
                                comment_author = comment.get('nickname', '匿名用户')
                                comment_content = comment.get('content', '')
                                
                                # 绘制评论作者和内容
                                comment_text = f'{comment_author}: {comment_content}'
                                comment_lines = self._wrap_text(comment_text, c, 'chinese' if font_registered else 'Helvetica', 12, text_width-20)
                                
                                for i, line in enumerate(comment_lines):
                                    c.drawString(margin+20, y, line)
                                    y -= 20
                                    # 检查是否需要新页面
                                    if y < 100:
                                        c.showPage()
                                        if font_registered:
                                            c.setFont('chinese', 12)
                                        else:
                                            c.setFont('Helvetica', 12)
                                        y = height - margin
                            
                                # 添加回复
                                replies = comment.get('reply_list', [])
                                for reply in replies:
                                    try:
                                        # 检查是否需要新页面
                                        if y < 100:
                                            c.showPage()
                                            if font_registered:
                                                c.setFont('chinese', 12)
                                            else:
                                                c.setFont('Helvetica', 12)
                                            y = height - margin
                                        
                                        reply_author = reply.get('nickname', '匿名用户')
                                        reply_to = reply.get('reply_nickname', '匿名用户')
                                        reply_content = reply.get('content', '')
                                        
                                        # 绘制回复
                                        reply_text = f'  ↪ {reply_author} 回复 {reply_to}: {reply_content}'
                                        reply_lines = self._wrap_text(reply_text, c, 'chinese' if font_registered else 'Helvetica', 12, text_width-40)
                                        
                                        for line in reply_lines:
                                            c.drawString(margin+40, y, line)
                                            y -= 20
                                            # 检查是否需要新页面
                                            if y < 100:
                                                c.showPage()
                                                if font_registered:
                                                    c.setFont('chinese', 12)
                                                else:
                                                    c.setFont('Helvetica', 12)
                                                y = height - margin
                                    except Exception as e:
                                        self.log(f"绘制回复出错: {e}")
                                        c.drawString(margin+40, y, '[回复显示错误]')
                                        y -= 20
                                
                                y -= 10
                            except Exception as e:
                                self.log(f"绘制评论出错: {e}")
                                c.drawString(margin+20, y, '[评论显示错误]')
                                y -= 20
                    
                    y -= 30
                except Exception as e:
                    self.log(f"处理帖子时出错: {e}")
                    c.drawString(margin, y, f'处理帖子出错: {str(e)}')
                    y -= 30
                    continue
            
            # 保存PDF
            self.log("正在保存PDF文件...")
            c.save()
            self.log(f"PDF报告生成成功: {pdf_path}")
            
            # 显示成功消息
            QMessageBox.information(self, "成功", f"PDF报告已生成并保存到:\n{pdf_path}")
            
        except Exception as e:
            error_msg = f"生成PDF报告时出错: {str(e)}"
            self.log(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            
            # 添加更多错误信息
            import traceback
            trace = traceback.format_exc()
            self.log(f"错误详情:\n{trace}")
            
    def _wrap_text(self, text, canvas_obj, font_name, font_size, max_width):
        """将文本按照指定宽度换行"""
        if not text:
            return [""]
            
        # 设置字体以便测量文本宽度
        canvas_obj.setFont(font_name, font_size)
        
        words = text.split()
        lines = []
        current_line = ""
        
        # 对于中文，按字符分割而不是按单词
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            # 中文文本处理
            current_line = ""
            for char in text:
                test_line = current_line + char
                # 测量当前行加上新字符的宽度
                if canvas_obj.stringWidth(test_line) < max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = char
            
            # 添加最后一行
            if current_line:
                lines.append(current_line)
        else:
            # 英文文本处理
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if canvas_obj.stringWidth(test_line) < max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            
            # 添加最后一行
            if current_line:
                lines.append(current_line)
                
        return lines

    def preview_data(self):
        """预览爬取的帖子列表"""
        if not self.fetched_data:
            QMessageBox.warning(self, "警告", "没有可预览的数据！请先爬取数据。")
            return
            
        try:
            # 创建并显示帖子列表窗口
            # 创建适合PostListWindow的数据结构
            preview_data = {"data": {"list": self.fetched_data}}
            self.post_list_window = PostListWindow(preview_data, self)
            self.post_list_window.show()
        except Exception as e:
            self.log(f"预览帖子时出错: {str(e)}")
            QMessageBox.critical(self, "预览失败", f"预览帖子时出错: {str(e)}")

    def backup_data(self):
        """备份已爬取的数据"""
        if not self.fetched_data:
            QMessageBox.warning(self, "警告", "没有数据可以备份！")
            return
            
        try:
            # 获取当前时间作为备份文件名的一部分
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_file = os.path.join(backup_dir, f"zanao_backup_{timestamp}.pkl")
            
            # 创建备份数据字典
            backup_data = {
                "fetched_data": self.fetched_data,
                "timestamp": timestamp,
                "page_count": self.page_spin.value(),
                "image_dir": self.img_save_dir
            }
            
            # 保存为pickle文件
            with open(backup_file, 'wb') as f:
                pickle.dump(backup_data, f)
                
            self.log(f"数据已成功备份到: {backup_file}")
            QMessageBox.information(self, "备份成功", f"数据已成功备份到:\n{backup_file}")
            self.statusBar.showMessage(f"备份完成: {timestamp}")
            
        except Exception as e:
            self.log(f"备份数据时出错: {str(e)}")
            QMessageBox.critical(self, "备份失败", f"备份数据时出错:\n{str(e)}")
    
    def restore_data(self):
        """恢复备份的数据"""
        try:
            backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
            if not os.path.exists(backup_dir):
                QMessageBox.warning(self, "警告", "没有找到备份目录！")
                return
                
            # 打开文件选择对话框
            options = QFileDialog.Options()
            backup_file, _ = QFileDialog.getOpenFileName(
                self, "选择备份文件", backup_dir,
                "备份文件 (*.pkl);;所有文件 (*)", options=options
            )
            
            if not backup_file:
                return  # 用户取消了操作
                
            # 加载备份数据
            with open(backup_file, 'rb') as f:
                backup_data = pickle.load(f)
                
            # 恢复数据
            self.fetched_data = backup_data.get("fetched_data", [])
            timestamp = backup_data.get("timestamp", "未知时间")
            
            # 更新UI
            self.log(f"已从备份恢复数据: {timestamp}")
            self.log(f"恢复了 {len(self.fetched_data)} 条帖子数据")
            
            # 启用相关按钮
            self.save_btn.setEnabled(True)
            self.pdf_btn.setEnabled(True)
            self.preview_btn.setEnabled(True)
            self.backup_btn.setEnabled(True)
            
            # 更新状态栏
            self.statusBar.showMessage(f"数据恢复完成，共 {len(self.fetched_data)} 条帖子")
            
            QMessageBox.information(self, "恢复成功", f"已成功恢复 {len(self.fetched_data)} 条帖子数据!")
            
        except Exception as e:
            self.log(f"恢复数据时出错: {str(e)}")
            QMessageBox.critical(self, "恢复失败", f"恢复数据时出错:\n{str(e)}")

def load_js_code(js_file_path):
    """
    从指定路径加载JavaScript代码。
    
    参数:
        js_file_path (str): JavaScript文件的路径。
        
    返回:
        str: JavaScript代码内容。
        
    异常:
        FileNotFoundError: 如果文件不存在。
    """
    try:
        with open(js_file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"错误: 找不到文件 '{js_file_path}'")
        raise

def get_js_result(js_code):
    """
    执行JavaScript代码并获取结果。

    参数:
        js_code (str): 要执行的JavaScript代码。
        
    返回:
        dict: 包含多个由JavaScript代码生成的键值对。
        
    异常:
        Exception: 如果JavaScript执行失败。
    """
    try:
        result = execjs.compile(js_code).call("get_result")
        return result
    except Exception as e:
        print(f"执行JavaScript时出错: {e}")
        raise

def get_headers(js_result):
    """
    生成并返回请求头。

    参数:
        js_result (dict): JavaScript执行结果。
        
    返回:
        dict: 包含HTTP请求所需的头部信息。
    """
    headers = {
        'Host': 'api.x.zanao.com',
        'x-sc-version': '3.0.4',
        'x-sc-nd': js_result["X-Sc-Nd"],
        'x-sc-cloud': '0',
        'x-sc-platform': 'windows',
        'x-sc-appid': 'wx3921ddb0258ff14f',
        'x-sc-alias': 'cqu',
        'x-sc-od': USER_TOKEN,
        'content-type': 'application/x-www-form-urlencoded',
        'x-sc-ah': js_result["X-Sc-Ah"],
        'xweb_xhr': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090c2d)XWEB/11581',
        'x-sc-td': str(js_result["X-Sc-Td"]),  # 将整数转换为字符串
        'accept': '*/*',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://servicewechat.com/wx3921ddb0258ff14f/60/page-frame.html',
        'accept-language': 'zh-CN,zh;q=0.9'
    }
    return headers

def get_params(timestamp):
    """
    根据提供的时间戳生成并返回请求参数。

    参数:
        timestamp (int): 时间戳。

    返回:
        dict: 包含HTTP请求所需的参数。
    """
    params = {
        "from_time": str(timestamp),
        "hot": "1"
    }
    return params

def process_data(data):
    """
    处理并格式化帖子数据。
    
    参数:
        data (dict): API返回的原始数据。
        
    返回:
        str: 格式化后的文本数据。
    """
    output = []
    try:
        for post in data['data']['list']:
            # 添加帖子ID
            thread_id = post.get('thread_id', '未知ID')
            output.append(f"🆔 帖子ID：{thread_id}")
            output.append(f"📌 标题：{post['title']}")
            output.append(f"📝 内容：{post['content']}")
            output.append(f"👤 作者：{post['nickname']} ({post.get('user_level_title', '普通用户')})")
            
            # 添加图片信息
            img_paths = post.get('img_paths', [])
            if img_paths:
                output.append(f"🖼️ 图片数量：{len(img_paths)}")
                for i, img_path in enumerate(img_paths):
                    output.append(f"   图片{i+1}：{img_path}")
            
            # 使用post_time显示相对时间，同时使用p_time显示具体时间
            post_time = post.get('post_time', '未知时间')
            p_time_stamp = int(post.get('p_time', time.time()))
            p_time_str = datetime.fromtimestamp(p_time_stamp).strftime('%Y-%m-%d %H:%M:%S')
            
            output.append(f"⏰ 发布时间：{post_time} ({p_time_str})")
            output.append(f"💬 评论数：{post.get('c_count', 0)} | 👍 点赞：{post.get('l_count', 0)}\n")
            
            # 处理评论
            for comment in post.get('comment_list', []):
                comment_id = comment.get('comment_id', '未知ID')
                output.append(f"    💬 评论ID: {comment_id} | {comment.get('nickname', '匿名用户')}：{comment.get('content', '')}")
                
                # 处理回复
                for reply in comment.get('reply_list', []):
                    reply_id = reply.get('comment_id', '未知ID')
                    output.append(f"        ↪️ 回复ID: {reply_id} | {reply.get('nickname', '匿名用户')} 回复 {reply.get('reply_nickname', '匿名用户')}：{reply.get('content', '')}")
            
            output.append("\n" + "━"*50 + "\n")
    except KeyError as e:
        print(f"处理数据时出错: 找不到键 {e}")
        # 将原始数据结构打印出来，以便调试
        print("原始数据结构:")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:500] + "...")  # 只打印前500个字符
        raise
    
    return "\n".join(output)

def save_data(data, filename, is_json=False):
    """
    保存数据到文件。
    
    参数:
        data: 要保存的数据。
        filename (str): 文件名。
        is_json (bool): 是否以JSON格式保存。
        
    返回:
        bool: 保存是否成功。
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            if is_json:
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                f.write(data)
        return True
    except Exception as e:
        print(f"保存文件 '{filename}' 时出错: {e}")
        return False

def main():
    """主函数，启动GUI应用程序"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion风格，在所有平台上看起来都很现代
    
    # 设置应用程序图标（如果有的话）
    # app.setWindowIcon(QIcon('icon.png'))
    
    # 创建并显示主窗口
    window = ZanaoGUI()
    window.show()
    
    # 运行应用程序事件循环
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weirdhost 续期和启动脚本 - GitHub Actions 版本
合并版本：先续期后启动
针对CF五秒盾修复版本
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright, TimeoutError, expect


class WeirdhostAuto:
    def __init__(self):
        """初始化，从环境变量读取配置"""
        self.url = os.getenv('WEIRDHOST_URL', 'https://hub.weirdhost.xyz')
        self.server_urls = os.getenv('WEIRDHOST_SERVER_URLS', '')
        self.login_url = os.getenv('WEIRDHOST_LOGIN_URL', 'https://hub.weirdhost.xyz/auth/login')
        
        # 获取认证信息
        self.remember_web_cookie = os.getenv('REMEMBER_WEB_COOKIE', '')
        self.email = os.getenv('WEIRDHOST_EMAIL', '')
        self.password = os.getenv('WEIRDHOST_PASSWORD', '')
        
        # 浏览器配置
        self.headless = os.getenv('HEADLESS', 'true').lower() == 'true'
        self.slow_mo = int(os.getenv('SLOW_MO', '100'))  # 添加延迟模拟人类操作
        
        # 解析服务器URL列表
        self.server_list = []
        if self.server_urls:
            self.server_list = [url.strip() for url in self.server_urls.split(',') if url.strip()]
        
        # 存储每个服务器的结果
        self.server_results = {}
    
    def log(self, message, level="INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")
    
    def has_cookie_auth(self):
        """检查是否有 cookie 认证信息"""
        return bool(self.remember_web_cookie)
    
    def has_email_auth(self):
        """检查是否有邮箱密码认证信息"""
        return bool(self.email and self.password)
    
    def check_login_status(self, page):
        """检查是否已登录"""
        try:
            self.log("检查登录状态...")
            
            # 简单检查：如果URL包含login或auth，说明未登录
            if "login" in page.url or "auth" in page.url:
                self.log("当前在登录页面，未登录")
                return False
            else:
                self.log("不在登录页面，判断为已登录")
                return True
                
        except Exception as e:
            self.log(f"检查登录状态时出错: {e}", "ERROR")
            return False
    
    def login_with_cookies(self, context):
        """使用 Cookies 登录"""
        try:
            self.log("尝试使用 Cookies 登录...")
            
            # 创建cookie
            session_cookie = {
                'name': 'remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d',
                'value': self.remember_web_cookie,
                'domain': 'hub.weirdhost.xyz',
                'path': '/',
                'expires': int(time.time()) + 3600 * 24 * 365,
                'httpOnly': True,
                'secure': True,
                'sameSite': 'Lax'
            }
            
            context.add_cookies([session_cookie])
            self.log("已添加 remember_web cookie")
            return True
                
        except Exception as e:
            self.log(f"设置 Cookies 时出错: {e}", "ERROR")
            return False
    
    def login_with_email(self, page):
        """使用邮箱密码登录"""
        try:
            self.log("尝试使用邮箱密码登录...")
            
            # 访问登录页面
            self.log(f"访问登录页面: {self.login_url}")
            page.goto(self.login_url, wait_until="domcontentloaded")
            
            # 使用固定选择器
            email_selector = 'input[name="username"]'
            password_selector = 'input[name="password"]'
            login_button_selector = 'button[type="submit"]'
            
            # 等待元素加载
            self.log("等待登录表单元素加载...")
            page.wait_for_selector(email_selector)
            page.wait_for_selector(password_selector)
            page.wait_for_selector(login_button_selector)
            
            # 填写登录信息
            self.log("填写邮箱和密码...")
            page.fill(email_selector, self.email)
            time.sleep(1)  # 模拟人类输入
            page.fill(password_selector, self.password)
            time.sleep(1)
            
            # 点击登录并等待导航
            self.log("点击登录按钮...")
            with page.expect_navigation(wait_until="domcontentloaded", timeout=90000):
                page.click(login_button_selector)
            
            # 检查登录是否成功
            if "login" in page.url or "auth" in page.url:
                self.log("邮箱密码登录失败，仍在登录页面", "ERROR")
                return False
            else:
                self.log("邮箱密码登录成功！")
                return True
                
        except Exception as e:
            self.log(f"邮箱密码登录时出错: {e}", "ERROR")
            return False
    
    def handle_cf_challenge(self, page, server_id):
        """处理CF五秒盾挑战"""
        try:
            self.log(f"检查服务器 {server_id} 是否遇到CF挑战...")
            
            # 检查是否有CF挑战页面
            cf_selectors = [
                '#challenge-form',
                '.challenge-form',
                '#challenge-running',
                '#cf-content',
                '#challenge-stage',
                'text=Checking your browser'
            ]
            
            for selector in cf_selectors:
                try:
                    if page.locator(selector).is_visible(timeout=3000):
                        self.log(f"⚠️ 服务器 {server_id} 检测到CF挑战，正在等待...")
                        
                        # 等待CF挑战完成（通常5-10秒）
                        wait_time = 10
                        self.log(f"等待 {wait_time} 秒让CF挑战完成...")
                        time.sleep(wait_time)
                        
                        # 检查挑战是否完成
                        if page.locator(selector).is_visible(timeout=3000):
                            self.log(f"⚠️ 服务器 {server_id} CF挑战仍然存在，继续等待...")
                            time.sleep(5)
                        
                        self.log(f"✅ 服务器 {server_id} CF挑战处理完成")
                        return True
                except:
                    continue
            
            # 检查是否有"Verify you are human"等文本
            cf_texts = ["Checking your browser", "Verify", "Security Check", "Cloudflare"]
            page_text = page.content().lower()
            
            for text in cf_texts:
                if text.lower() in page_text:
                    self.log(f"⚠️ 服务器 {server_id} 检测到CF相关文本，等待挑战...")
                    time.sleep(10)
                    return True
            
            return False
            
        except Exception as e:
            self.log(f"检查CF挑战时出错: {e}", "WARNING")
            return False
    
    def wait_for_page_ready(self, page, server_id, operation="操作"):
        """等待页面完全就绪，增加CF挑战处理"""
        self.log(f"等待服务器 {server_id} {operation}页面加载...")
        
        # 首先处理可能的CF挑战
        self.handle_cf_challenge(page, server_id)
        
        # 等待主要内容区域加载
        try:
            page.wait_for_selector('.server-details, .server-info, .card, .panel, .container, main, article', timeout=15000)
            self.log(f"✅ 服务器 {server_id} 主要内容已加载")
        except:
            self.log(f"⚠️ 服务器 {server_id} 未找到主要内容区域")
        
        # 等待所有图片加载完成
        try:
            page.wait_for_load_state('networkidle', timeout=20000)
            self.log(f"✅ 服务器 {server_id} 网络空闲")
        except:
            self.log(f"⚠️ 服务器 {server_id} 网络未完全空闲")
        
        # 额外等待时间确保动态内容加载，特别是CF挑战后
        time.sleep(3)
        
        # 再次检查CF挑战
        self.handle_cf_challenge(page, server_id)
    
    def find_renew_button(self, page, server_id):
        """查找续期按钮 - 使用多种方法"""
        selectors = [
            'button:has-text("시간추가")',
            'button:has-text("시간 추가")',
            '//button[contains(text(), "시간추가")]',
            '//button[contains(text(), "시간 추가")]',
            'button:has-text("Renew")',
            'button:has-text("Add Time")',
        ]
        
        # 先等待页面稳定
        time.sleep(2)
        
        for selector in selectors:
            try:
                if selector.startswith('//'):
                    button = page.locator(f'xpath={selector}')
                else:
                    button = page.locator(selector)
                
                # 使用更严格的可见性检查
                button.wait_for(state='visible', timeout=8000)
                
                if button.is_visible():
                    self.log(f"✅ 服务器 {server_id} 找到续期按钮: {selector}")
                    return button
                    
            except Exception as e:
                continue
        
        # 如果上述方法都失败，尝试更广泛的搜索
        return self.find_button_alternative_methods(page, server_id, ["시간", "Renew", "Add", "추가"])
    
    def find_start_button(self, page, server_id):
        """查找启动按钮 - 完全匹配 Start"""
        selectors = [
            'button:has-text("Start")',
            '//button[text()="Start"]',
            'button:has-text("Start Server")',
            'button:has-text("시작")',
            '//button[contains(text(), "Start")]',
        ]
        
        for selector in selectors:
            try:
                if selector.startswith('//'):
                    button = page.locator(f'xpath={selector}')
                else:
                    button = page.locator(selector)
                
                # 使用更严格的可见性检查
                button.wait_for(state='visible', timeout=8000)
                
                if button.is_visible():
                    self.log(f"✅ 服务器 {server_id} 找到启动按钮: {selector}")
                    return button
                    
            except Exception as e:
                continue
        
        # 如果上述方法都失败，尝试更广泛的搜索
        return self.find_button_alternative_methods(page, server_id, ["Start", "시작"], exact_match=True)
    
    def find_button_alternative_methods(self, page, server_id, keywords, exact_match=False):
        """备用的按钮查找方法"""
        # 方法1: 查找所有按钮并筛选
        try:
            all_buttons = page.locator('button')
            button_count = all_buttons.count()
            
            for i in range(button_count):
                try:
                    button = all_buttons.nth(i)
                    if button.is_visible():
                        text = button.text_content().strip()
                        
                        if exact_match:
                            # 完全匹配
                            if any(keyword == text for keyword in keywords):
                                self.log(f"✅ 服务器 {server_id} 通过文本搜索找到按钮: '{text}'")
                                return button
                        else:
                            # 包含匹配
                            if any(keyword in text for keyword in keywords):
                                self.log(f"✅ 服务器 {server_id} 通过文本搜索找到按钮: '{text}'")
                                return button
                except:
                    continue
        except:
            pass
        
        # 方法2: 查找特定class的按钮
        try:
            primary_buttons = page.locator('button.btn-primary, button.btn-success, button.btn-info, button.is-primary, .btn, .button')
            if primary_buttons.count() > 0:
                for i in range(primary_buttons.count()):
                    button = primary_buttons.nth(i)
                    if button.is_visible():
                        text = button.text_content().strip()
                        
                        if exact_match:
                            if any(keyword == text for keyword in keywords):
                                self.log(f"✅ 服务器 {server_id} 通过class找到按钮")
                                return button
                        else:
                            if any(keyword in text for keyword in keywords):
                                self.log(f"✅ 服务器 {server_id} 通过class找到按钮")
                                return button
        except:
            pass
        
        self.log(f"❌ 服务器 {server_id} 所有方法都未找到按钮")
        return None
    
    def renew_server(self, page, server_url):
        """续期服务器，增加CF挑战处理"""
        try:
            server_id = server_url.split('/')[-1]
            self.log(f"📅 开始续期服务器 {server_id}")
            
            # 访问服务器页面
            self.log(f"访问服务器页面: {server_url}")
            page.goto(server_url, wait_until="networkidle")
            
            # 等待页面加载，包含CF挑战处理
            self.wait_for_page_ready(page, server_id, "续期")
            
            # 查找续期按钮
            button = self.find_renew_button(page, server_id)
            
            if not button:
                self.log(f"❌ 服务器 {server_id} 未找到续期按钮")
                return "no_renew_button"
            
            # 检查按钮是否被CF屏蔽
            if not button.is_enabled():
                self.log(f"⚠️ 服务器 {server_id} 续期按钮不可点击，可能被CF屏蔽，等待后重试...")
                time.sleep(5)
                
                # 刷新页面重试
                page.reload(wait_until="networkidle")
                self.wait_for_page_ready(page, server_id, "续期重试")
                
                button = self.find_renew_button(page, server_id)
                if not button or not button.is_enabled():
                    self.log(f"❌ 服务器 {server_id} 续期按钮仍然不可点击")
                    return "renew_button_disabled"
            
            # 点击按钮并检查结果
            return self.click_renew_button_and_check(page, button, server_id)
                
        except Exception as e:
            self.log(f"❌ 服务器 {server_id} 续期过程中出错: {e}")
            return "renew_error"
    
    def click_renew_button_and_check(self, page, button, server_id):
        """点击续期按钮并检查结果"""
        try:
            if button.is_enabled():
                # 点击前保存页面状态用于比较
                before_click = page.content()
                
                self.log(f"✅ 服务器 {server_id} 续期按钮可点击，正在点击...")
                
                # 模拟人类操作：鼠标移动到按钮上
                button.hover()
                time.sleep(1)
                
                # 点击按钮
                button.click()
                
                # 等待页面响应，增加等待时间处理可能的CF验证
                time.sleep(8)
                
                # 检查是否出现CF挑战
                self.handle_cf_challenge(page, server_id)
                
                # 检查页面变化
                after_click = page.content()
                
                # 检查是否出现错误消息
                error_patterns = [
                    "already renewed", "can't renew", "only once", 
                    "이미", "한번", "불가능", "already added",
                    "failed", "error", "오류"
                ]
                
                has_error = any(pattern.lower() in after_click.lower() for pattern in error_patterns)
                
                if has_error:
                    self.log(f"ℹ️ 服务器 {server_id} 检测到重复续期提示")
                    return "already_renewed"
                else:
                    # 检查是否有成功消息
                    success_patterns = ["success", "성공", "added", "추가됨", "시간이 추가", "추가되었습니다"]
                    has_success = any(pattern.lower() in after_click.lower() for pattern in success_patterns)
                    
                    if has_success:
                        self.log(f"✅ 服务器 {server_id} 续期成功")
                        return "renew_success"
                    else:
                        # 检查页面内容是否发生变化
                        if before_click != after_click:
                            self.log(f"⚠️ 服务器 {server_id} 页面已变化但无明确结果")
                            return "renew_unknown_changed"
                        else:
                            self.log(f"⚠️ 服务器 {server_id} 页面无变化")
                            return "renew_no_change"
            else:
                self.log(f"❌ 服务器 {server_id} 续期按钮不可点击")
                return "renew_button_disabled"
                
        except Exception as e:
            self.log(f"❌ 服务器 {server_id} 点击续期按钮时出错: {e}")
            return "renew_click_error"
    
    def start_server(self, page, server_url):
        """启动服务器"""
        try:
            server_id = server_url.split('/')[-1]
            self.log(f"🚀 开始启动服务器 {server_id}")
            
            # 刷新页面确保最新状态
            page.reload(wait_until="networkidle")
            
            # 等待页面加载，包含CF挑战处理
            self.wait_for_page_ready(page, server_id, "启动")
            
            # 查找启动按钮
            button = self.find_start_button(page, server_id)
            
            if not button:
                self.log(f"❌ 服务器 {server_id} 未找到Start按钮")
                return "no_start_button"
            
            # 检查按钮是否被CF屏蔽
            if not button.is_enabled():
                self.log(f"⚠️ 服务器 {server_id} Start按钮不可点击，可能被CF屏蔽，等待后重试...")
                time.sleep(5)
                
                # 再次查找按钮
                button = self.find_start_button(page, server_id)
                if not button or not button.is_enabled():
                    self.log(f"ℹ️ 服务器 {server_id} 已启动，按钮不可点击")
                    return "already_started"
            
            # 检查按钮状态并处理
            if button.is_enabled():
                self.log(f"✅ 服务器 {server_id} 可以启动，正在点击...")
                
                # 模拟人类操作
                button.hover()
                time.sleep(1)
                button.click()
                
                # 等待操作完成
                time.sleep(8)
                
                # 检查是否出现CF挑战
                self.handle_cf_challenge(page, server_id)
                
                # 检查是否启动成功
                # 重新查找按钮，检查是否变为不可用或其他状态
                try:
                    new_button = self.find_start_button(page, server_id)
                    if new_button and not new_button.is_enabled():
                        self.log(f"✅ 服务器 {server_id} 启动成功，按钮状态已变化")
                        return "start_success"
                    else:
                        # 检查是否有成功消息
                        page_content = page.content().lower()
                        if "started" in page_content or "running" in page_content or "启动" in page_content or "시작" in page_content:
                            self.log(f"✅ 服务器 {server_id} 启动成功")
                            return "start_success"
                        else:
                            self.log(f"⚠️ 服务器 {server_id} 启动操作完成，但状态未知")
                            return "start_unknown"
                except:
                    self.log(f"⚠️ 服务器 {server_id} 启动操作完成，无法验证状态")
                    return "start_unknown"
            else:
                self.log(f"ℹ️ 服务器 {server_id} 已启动，按钮不可点击")
                return "already_started"
                
        except Exception as e:
            self.log(f"❌ 服务器 {server_id} 启动过程中出错: {e}")
            return "start_error"
    
    def process_server(self, page, server_url):
        """处理单个服务器的续期和启动操作"""
        server_id = server_url.split('/')[-1] if server_url else "unknown"
        self.log(f"🔧 开始处理服务器 {server_id}")
        
        # 初始化服务器结果
        self.server_results[server_id] = {
            'renew_status': '未执行',
            'start_status': '未执行'
        }
        
        try:
            # 访问服务器页面
            self.log(f"访问服务器页面: {server_url}")
            page.goto(server_url, wait_until="networkidle")
            
            # 首先处理可能的CF挑战
            self.handle_cf_challenge(page, server_id)
            
            # 检查是否已登录
            if not self.check_login_status(page):
                self.log(f"服务器 {server_id} 未登录，尝试重新登录", "WARNING")
                self.server_results[server_id]['renew_status'] = 'login_failed'
                self.server_results[server_id]['start_status'] = 'login_failed'
                return f"{server_id}: login_failed"
            
            # 第一步：执行续期操作
            self.log(f"第一步：执行续期操作")
            renew_result = self.renew_server(page, server_url)
            self.server_results[server_id]['renew_status'] = renew_result
            
            # 等待一下，确保续期操作完成
            time.sleep(5)
            
            # 第二步：执行启动操作
            self.log(f"第二步：执行启动操作")
            start_result = self.start_server(page, server_url)
            self.server_results[server_id]['start_status'] = start_result
            
            # 返回组合结果
            combined_result = f"renew:{renew_result},start:{start_result}"
            self.log(f"✅ 服务器 {server_id} 处理完成: {combined_result}")
            
            return f"{server_id}: {combined_result}"
            
        except Exception as e:
            self.log(f"❌ 处理服务器 {server_id} 时出错: {e}", "ERROR")
            self.server_results[server_id]['renew_status'] = 'error'
            self.server_results[server_id]['start_status'] = 'error'
            return f"{server_id}: error"
    
    def run(self):
        """主运行函数"""
        self.log("开始 Weirdhost 自动续期和启动任务")
        
        # 检查认证信息
        has_cookie = self.has_cookie_auth()
        has_email = self.has_email_auth()
        
        self.log(f"Cookie 认证可用: {has_cookie}")
        self.log(f"邮箱密码认证可用: {has_email}")
        
        if not has_cookie and not has_email:
            self.log("没有可用的认证信息！", "ERROR")
            return ["error: no_auth"]
        
        # 检查服务器URL列表
        if not self.server_list:
            self.log("未设置服务器URL列表！请设置 WEIRDHOST_SERVER_URLS 环境变量", "ERROR")
            return ["error: no_servers"]
        
        self.log(f"需要处理的服务器数量: {len(self.server_list)}")
        for i, server_url in enumerate(self.server_list, 1):
            self.log(f"服务器 {i}: {server_url}")
        
        results = []
        
        try:
            with sync_playwright() as p:
                # 启动浏览器，增加一些参数绕过检测
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-web-security',
                        '--disable-features=site-per-process'
                    ]
                )
                
                # 创建浏览器上下文
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                # 创建页面
                page = context.new_page()
                page.set_default_timeout(120000)  # 增加超时时间
                page.set_default_navigation_timeout(120000)
                
                login_success = False
                
                # 方案1: 尝试 Cookie 登录
                if has_cookie:
                    if self.login_with_cookies(context):
                        # 访问任意页面检查登录状态
                        self.log("检查Cookie登录状态...")
                        page.goto(self.url, wait_until="domcontentloaded")
                        
                        # 处理可能的CF挑战
                        self.handle_cf_challenge(page, "登录检查")
                        
                        if self.check_login_status(page):
                            self.log("✅ Cookie 登录成功！")
                            login_success = True
                        else:
                            self.log("Cookie 登录失败，cookies 可能已过期", "WARNING")
                
                # 方案2: 如果 Cookie 登录失败，尝试邮箱密码登录
                if not login_success and has_email:
                    if self.login_with_email(page):
                        # 登录成功后访问首页
                        self.log("检查邮箱密码登录状态...")
                        page.goto(self.url, wait_until="domcontentloaded")
                        
                        # 处理可能的CF挑战
                        self.handle_cf_challenge(page, "登录检查")
                        
                        if self.check_login_status(page):
                            self.log("✅ 邮箱密码登录成功！")
                            login_success = True
                
                # 如果登录成功，依次处理每个服务器
                if login_success:
                    for server_url in self.server_list:
                        result = self.process_server(page, server_url)
                        results.append(result)
                        self.log(f"服务器处理结果: {result}")
                        
                        # 在处理下一个服务器前等待一下
                        time.sleep(8)
                else:
                    self.log("❌ 所有登录方式都失败了", "ERROR")
                    results = ["login_failed"] * len(self.server_list)
                
                browser.close()
                return results
                
        except TimeoutError as e:
            self.log(f"操作超时: {e}", "ERROR")
            return ["error: timeout"] * len(self.server_list)
        except Exception as e:
            self.log(f"运行时出错: {e}", "ERROR")
            return ["error: runtime"] * len(self.server_list)
    
    def write_readme_file(self, results):
        """写入README文件"""
        try:
            # 获取东八区时间
            beijing_time = datetime.now(timezone(timedelta(hours=8)))
            timestamp = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 状态消息映射
            status_messages = {
                # 续期状态
                "renew_success": "✅ 续期成功",
                "already_renewed": "🔄 已经续期过",
                "no_renew_button": "❌ 未找到续期按钮",
                "renew_button_disabled": "❌ 续期按钮不可用(可能被CF屏蔽)",
                "renew_unknown_changed": "⚠️ 续期页面变化但结果未知",
                "renew_no_change": "⚠️ 续期页面无变化",
                "renew_click_error": "💥 点击续期按钮出错",
                "renew_error": "💥 续期过程出错",
                
                # 启动状态
                "start_success": "✅ 启动成功",
                "already_started": "🔄 已经启动",
                "no_start_button": "❌ 未找到Start按钮",
                "start_unknown": "⚠️ 启动完成但状态未知",
                "start_error": "💥 启动过程出错",
                
                # 通用状态
                "login_failed": "❌ 登录失败",
                "error": "💥 运行出错",
                "未执行": "⏸️ 未执行",
                
                # 错误状态
                "error: no_auth": "❌ 无认证信息",
                "error: no_servers": "❌ 无服务器配置",
                "error: timeout": "⏰ 操作超时",
                "error: runtime": "💥 运行时错误"
            }
            
            # 创建README内容
            readme_content = f"""# Weirdhost 自动续期和启动脚本

**最后运行时间**: `{timestamp}` (北京时间)

**注意**: 此版本已针对CF五秒盾进行优化，增加了等待和检测逻辑

## 运行结果

| 服务器ID | 续期状态 | 启动状态 |
|----------|----------|----------|
"""
            
            # 添加每个服务器的结果表格
            for server_id, status in self.server_results.items():
                renew_msg = status_messages.get(status['renew_status'], f"❓ {status['renew_status']}")
                start_msg = status_messages.get(status['start_status'], f"❓ {status['start_status']}")
                readme_content += f"| `{server_id}` | {renew_msg} | {start_msg} |\n"
            
            # 如果没有服务器结果，显示错误信息
            if not self.server_results:
                for result in results:
                    if ":" in result and not result.startswith("error:"):
                        parts = result.split(":", 1)
                        server_id = parts[0].strip()
                        status = parts[1].strip() if len(parts) > 1 else "unknown"
                        status_msg = status_messages.get(status, f"❓ 未知状态 ({status})")
                        readme_content += f"| `{server_id}` | {status_msg} | N/A |\n"
                    else:
                        status_msg = status_messages.get(result, f"❓ 未知状态 ({result})")
                        readme_content += f"| 未知 | {status_msg} | N/A |\n"
            
            # 添加统计信息
            total_servers = len(self.server_list)
            successful_renews = sum(1 for s in self.server_results.values() 
                                  if s['renew_status'] in ['renew_success', 'already_renewed'])
            successful_starts = sum(1 for s in self.server_results.values() 
                                  if s['start_status'] in ['start_success', 'already_started'])
            
            readme_content += f"""
## 统计信息

- 总服务器数: {total_servers}
- 成功续期: {successful_renews}/{total_servers}
- 成功启动: {successful_starts}/{total_servers}
- 运行时间: {timestamp}

## CF五秒盾处理说明

1. 脚本已增加CF挑战检测功能
2. 检测到CF挑战时会自动等待10-15秒
3. 如果按钮被CF屏蔽，会尝试刷新页面重试
4. 增加了人类行为模拟（延迟、悬停）

> 注意：如果续期按钮显示"不可用(可能被CF屏蔽)"，通常等待一段时间后重试即可。
> 脚本每天运行一次即可，多次运行不会有额外效果。
"""
            
            # 写入README文件
            with open('README.md', 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            self.log("📝 README已更新")
            
        except Exception as e:
            self.log(f"写入README文件失败: {e}", "ERROR")


def main():
    """主函数"""
    print("🚀 Weirdhost 自动续期和启动脚本启动 (CF五秒盾修复版)")
    print("=" * 50)
    
    # 创建自动操作器
    auto = WeirdhostAuto()
    
    # 检查环境变量
    if not auto.has_cookie_auth() and not auto.has_email_auth():
        print("❌ 错误：未设置认证信息！")
        print("\n请在 GitHub Secrets 中设置以下任一组合：")
        print("\n方案1 - Cookie 认证：")
        print("REMEMBER_WEB_COOKIE: 你的cookie值")
        print("\n方案2 - 邮箱密码认证：")
        print("WEIRDHOST_EMAIL: 你的邮箱")
        print("WEIRDHOST_PASSWORD: 你的密码")
        print("\n推荐使用 Cookie 认证，更稳定可靠")
        sys.exit(1)
    
    # 检查服务器URL列表
    if not auto.server_list:
        print("❌ 错误：未设置服务器URL列表！")
        print("\n请在 GitHub Secrets 中设置：")
        print("WEIRDHOST_SERVER_URLS: https://hub.weirdhost.xyz/server/服务器ID1,https://hub.weirdhost.xyz/server/服务器ID2")
        print("\n示例: https://hub.weirdhost.xyz/server/abc12345,https://hub.weirdhost.xyz/server/abc67890")
        sys.exit(1)
    
    print("🔧 配置检查通过")
    print(f"📋 服务器数量: {len(auto.server_list)}")
    print("⚠️  注意：此版本已针对CF五秒盾进行优化")
    print("=" * 50)
    
    # 执行自动任务
    results = auto.run()
    
    # 写入README文件
    auto.write_readme_file(results)
    
    print("=" * 50)
    print("📊 运行结果汇总:")
    
    # 显示详细结果
    for server_id, status in auto.server_results.items():
        print(f"\n服务器: {server_id}")
        print(f"  续期: {status['renew_status']}")
        print(f"  启动: {status['start_status']}")
    
    # 统计结果
    total = len(auto.server_list)
    renew_success = sum(1 for s in auto.server_results.values() 
                       if s['renew_status'] in ['renew_success', 'already_renewed'])
    start_success = sum(1 for s in auto.server_results.values() 
                       if s['start_status'] in ['start_success', 'already_started'])
    
    print("\n" + "=" * 50)
    print(f"📈 统计信息:")
    print(f"  总服务器数: {total}")
    print(f"  续期成功率: {renew_success}/{total}")
    print(f"  启动成功率: {start_success}/{total}")
    print("=" * 50)
    
    # 检查是否有完全失败的情况
    if any("login_failed" in result or "error:" in result for result in results):
        print("❌ 任务有失败的情况！")
        sys.exit(1)
    else:
        print("🎉 自动续期和启动任务完成！")
        sys.exit(0)


if __name__ == "__main__":
    main()
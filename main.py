#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weirdhost 登录脚本 - GitHub Actions 版本
支持 Cookie 登录和邮箱密码登录两种方式
支持多个服务器续期操作
"""

import os
import sys
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError


class WeirdhostLogin:
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
        
        # 解析服务器URL列表
        self.server_list = []
        if self.server_urls:
            self.server_list = [url.strip() for url in self.server_urls.split(',') if url.strip()]
    
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
            page.fill(password_selector, self.password)
            
            # 点击登录并等待导航
            self.log("点击登录按钮...")
            with page.expect_navigation(wait_until="domcontentloaded", timeout=60000):
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
    
    def add_server_time(self, page, server_url):
        """添加服务器时间（续期）"""
        try:
            self.log(f"开始执行续期操作: {server_url}")
            
            # 访问服务器页面
            self.log(f"访问服务器页面: {server_url}")
            page.goto(server_url, wait_until="domcontentloaded")
            
            # 等待页面加载
            time.sleep(3)
            
            # 查找 "시간추가" 按钮
            add_button_selector = 'button:has-text("시간추가")'
            self.log(f"正在查找 '{add_button_selector}' 按钮...")
            
            # 检查按钮是否存在且可见
            add_button = page.locator(add_button_selector)
            
            try:
                # 等待按钮出现，但不要等太久
                add_button.wait_for(state='visible', timeout=10000)
                
                # 检查按钮是否可点击
                if add_button.is_enabled():
                    # 点击按钮
                    add_button.click()
                    self.log("✅ 成功点击 '시간추가' 按钮")
                    
                    # 等待页面响应
                    time.sleep(3)
                    
                    # 检查是否出现重复续期的错误提示
                    error_messages = [
                        "You can't renew your server currently",
                        "you can only once at one time period",
                        "Request failed with status code 400"
                    ]
                    
                    page_content = page.content().lower()
                    for error_msg in error_messages:
                        if error_msg.lower() in page_content:
                            self.log("ℹ️  检测到重复续期提示，今天已经续期过了")
                            return "already_renewed"  # 返回特殊状态
                    
                    # 检查页面是否有错误提示元素
                    error_selectors = [
                        '.alert-danger',
                        '.error',
                        '[class*="error"]',
                        '.notification.is-danger'
                    ]
                    
                    for selector in error_selectors:
                        if page.locator(selector).is_visible(timeout=2000):
                            error_text = page.locator(selector).text_content()
                            if "can't renew" in error_text.lower() or "only once" in error_text.lower():
                                self.log(f"ℹ️  检测到续期限制提示: {error_text}")
                                return "already_renewed"  # 返回特殊状态
                    
                    self.log("✅ 续期操作完成！")
                    return "success"  # 返回成功状态
                else:
                    self.log("⚠️  '시간추가' 按钮存在但不可点击（可能今天已经续期过了）")
                    return "already_renewed"  # 返回特殊状态
                    
            except Exception:
                # 按钮不存在或不可见
                self.log("⚠️  未找到 '시간추가' 按钮（可能今天已经续期过了或按钮不可用）")
                return "already_renewed"  # 返回特殊状态
            
        except Exception as e:
            self.log(f"⚠️  续期操作遇到问题: {e}")
            self.log("ℹ️  这通常是正常情况，可能今天已经续期过了")
            return "already_renewed"  # 返回特殊状态
    
    def process_server(self, page, server_url):
        """处理单个服务器的续期操作"""
        server_id = server_url.split('/')[-1] if server_url else "unknown"
        self.log(f"开始处理服务器 {server_id}")
        
        try:
            # 访问服务器页面
            self.log(f"访问服务器页面: {server_url}")
            page.goto(server_url, wait_until="domcontentloaded")
            
            # 检查是否已登录
            if not self.check_login_status(page):
                self.log(f"服务器 {server_id} 未登录，尝试重新登录", "WARNING")
                return f"{server_id}: login_failed"
            
            # 执行续期操作
            result = self.add_server_time(page, server_url)
            return f"{server_id}: {result}"
            
        except Exception as e:
            self.log(f"处理服务器 {server_id} 时出错: {e}", "ERROR")
            return f"{server_id}: error"
    
    def run(self):
        """主运行函数"""
        self.log("开始 Weirdhost 自动续期任务")
        
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
                # 启动浏览器
                browser = p.chromium.launch(headless=self.headless)
                
                # 创建浏览器上下文
                context = browser.new_context()
                
                # 创建页面
                page = context.new_page()
                page.set_default_timeout(30000)
                
                login_success = False
                
                # 方案1: 尝试 Cookie 登录
                if has_cookie:
                    if self.login_with_cookies(context):
                        # 访问任意页面检查登录状态
                        self.log("检查Cookie登录状态...")
                        page.goto(self.url, wait_until="domcontentloaded")
                        
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
                        time.sleep(2)
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
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 状态消息映射
            status_messages = {
                "success": "✅ 续期成功",
                "already_renewed": "⚠️ 已经续期过了",
                "login_failed": "❌ 登录失败", 
                "error": "💥 运行出错",
                "error: no_auth": "❌ 无认证信息",
                "error: no_servers": "❌ 无服务器配置",
                "error: timeout": "⏰ 操作超时",
                "error: runtime": "💥 运行时错误"
            }
            
            # 创建README内容
            readme_content = f"""# Weirdhost 自动续期脚本

**最后运行时间**: `{timestamp}`

## 运行结果

"""
            
            # 添加每个服务器的结果
            for result in results:
                if ":" in result:
                    server_id, status = result.split(":", 1)
                    status = status.strip()
                    status_msg = status_messages.get(status, f"❓ 未知状态 ({status})")
                    readme_content += f"- 服务器 `{server_id}`: {status_msg}\n"
                else:
                    status_msg = status_messages.get(result, f"❓ 未知状态 ({result})")
                    readme_content += f"- {status_msg}\n"
            
            # 写入README文件
            with open('README.md', 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            self.log("📝 README已更新")
            
        except Exception as e:
            self.log(f"写入README文件失败: {e}", "ERROR")


def main():
    """主函数"""
    print("🚀 Weirdhost 自动续期脚本启动")
    print("=" * 50)
    
    # 创建登录器
    login = WeirdhostLogin()
    
    # 检查环境变量
    if not login.has_cookie_auth() and not login.has_email_auth():
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
    if not login.server_list:
        print("❌ 错误：未设置服务器URL列表！")
        print("\n请在 GitHub Secrets 中设置：")
        print("WEIRDHOST_SERVER_URLS: https://hub.weirdhost.xyz/server/服务器ID1,https://hub.weirdhost.xyz/server/服务器ID2")
        print("\n示例: https://hub.weirdhost.xyz/server/abc12345,https://hub.weirdhost.xyz/server/abc67890")
        sys.exit(1)
    
    # 执行续期任务
    results = login.run()
    
    # 写入README文件
    login.write_readme_file(results)
    
    print("=" * 50)
    print("📊 运行结果汇总:")
    for result in results:
        print(f"  - {result}")
    
    # 检查是否有完全失败的情况
    if any("login_failed" in result or "error:" in result for result in results):
        print("❌ 续期任务有失败的情况！")
        sys.exit(1)
    else:
        print("🎉 续期任务完成！")
        sys.exit(0)


if __name__ == "__main__":
    main()
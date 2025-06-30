#!/usr/bin/env python3
"""
WebData CLI - Web data extraction tool for AI assistants
"""

import asyncio
import json
import websockets
import click
import subprocess
import time
import os
import shutil
import threading
import schedule
import base64
from pathlib import Path
from rich.console import Console
from rich.table import Table
from typing import Dict, List, Optional, Any
import aiofiles

# Selenium imports (optional)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

console = Console()

class AutoCleaner:
    """Automatic data cleanup service"""

    def __init__(self):
        self.data_dir = Path("data")
        self.logs_dir = Path("logs")
        self.config_file = Path("webdata_config.json")
        self.is_running = False
        self.thread = None

    def load_config(self):
        """Load cleanup configuration"""
        default_config = {
            "auto_cleanup_enabled": True,
            "cleanup_interval_hours": 24,
            "max_file_age_hours": 48,
            "max_files_count": 100,
            "max_total_size_mb": 100
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            except:
                pass

        return default_config

    def save_config(self, config):
        """Save cleanup configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            console.print(f"Failed to save config: {e}", style="red")

    def cleanup_old_files(self, max_age_hours=48):
        """Clean files older than specified hours"""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)

        cleaned_files = []
        total_size = 0

        for directory in [self.data_dir, self.logs_dir]:
            if not directory.exists():
                continue

            for file_path in directory.iterdir():
                if file_path.is_file():
                    file_time = file_path.stat().st_mtime
                    if file_time < cutoff_time:
                        file_size = file_path.stat().st_size
                        total_size += file_size
                        file_path.unlink()
                        cleaned_files.append(str(file_path))

        return cleaned_files, total_size

    def cleanup_by_count(self, max_files=100):
        """Keep only the most recent N files"""
        cleaned_files = []
        total_size = 0

        for directory in [self.data_dir, self.logs_dir]:
            if not directory.exists():
                continue

            files = [f for f in directory.iterdir() if f.is_file()]
            if len(files) <= max_files:
                continue

            # Sort by modification time, oldest first
            files.sort(key=lambda x: x.stat().st_mtime)
            files_to_remove = files[:-max_files]

            for file_path in files_to_remove:
                file_size = file_path.stat().st_size
                total_size += file_size
                file_path.unlink()
                cleaned_files.append(str(file_path))

        return cleaned_files, total_size

    def cleanup_by_size(self, max_size_mb=100):
        """Remove oldest files if total size exceeds limit"""
        max_size_bytes = max_size_mb * 1024 * 1024
        cleaned_files = []
        total_cleaned_size = 0

        for directory in [self.data_dir, self.logs_dir]:
            if not directory.exists():
                continue

            files = [f for f in directory.iterdir() if f.is_file()]
            if not files:
                continue

            # Calculate total size
            total_size = sum(f.stat().st_size for f in files)
            if total_size <= max_size_bytes:
                continue

            # Sort by modification time, oldest first
            files.sort(key=lambda x: x.stat().st_mtime)

            current_size = total_size
            for file_path in files:
                if current_size <= max_size_bytes:
                    break

                file_size = file_path.stat().st_size
                current_size -= file_size
                total_cleaned_size += file_size
                file_path.unlink()
                cleaned_files.append(str(file_path))

        return cleaned_files, total_cleaned_size

    def auto_cleanup(self):
        """Perform automatic cleanup based on configuration"""
        config = self.load_config()

        if not config["auto_cleanup_enabled"]:
            return

        try:
            # Cleanup by age
            age_files, age_size = self.cleanup_old_files(config["max_file_age_hours"])

            # Cleanup by count
            count_files, count_size = self.cleanup_by_count(config["max_files_count"])

            # Cleanup by size
            size_files, size_size = self.cleanup_by_size(config["max_total_size_mb"])

            # Combine results
            all_cleaned_files = list(set(age_files + count_files + size_files))
            total_size = age_size + count_size + size_size

            if all_cleaned_files:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                console.print(f"[{timestamp}] Auto-cleanup: Removed {len(all_cleaned_files)} files ({total_size:,} bytes)", style="yellow")

                # Log cleanup activity
                self.logs_dir.mkdir(exist_ok=True)
                log_file = self.logs_dir / "auto_cleanup.log"
                with open(log_file, "a") as f:
                    f.write(f"{timestamp}: Cleaned {len(all_cleaned_files)} files ({total_size} bytes)\n")

        except Exception as e:
            console.print(f"Auto-cleanup error: {e}", style="red")

    def start_scheduler(self):
        """Start the automatic cleanup scheduler"""
        if self.is_running:
            return

        config = self.load_config()
        if not config["auto_cleanup_enabled"]:
            return

        try:
            import schedule

            # Schedule cleanup
            schedule.every(config["cleanup_interval_hours"]).hours.do(self.auto_cleanup)

            def run_scheduler():
                while self.is_running:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute

            self.is_running = True
            self.thread = threading.Thread(target=run_scheduler, daemon=True)
            self.thread.start()

            console.print(f"Auto-cleanup scheduler started (every {config['cleanup_interval_hours']} hours)", style="green")

        except ImportError:
            console.print("Schedule library not available. Install with: pip install schedule", style="yellow")
        except Exception as e:
            console.print(f"Failed to start scheduler: {e}", style="red")

    def stop_scheduler(self):
        """Stop the automatic cleanup scheduler"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1)
        console.print("Auto-cleanup scheduler stopped", style="yellow")

# Global auto-cleaner instance
auto_cleaner = AutoCleaner()

class ScreenStreamer:
    """Real-time screen streaming for Chrome"""

    def __init__(self, debug_port=9222):
        self.debug_port = debug_port
        self.is_streaming = False
        self.stream_thread = None
        self.latest_screenshot = None
        self.screenshot_interval = 1.0  # seconds
        self.output_dir = Path("stream")
        self.output_dir.mkdir(exist_ok=True)

    def start_streaming(self, interval=1.0, save_frames=False):
        """Start real-time screenshot streaming"""
        if self.is_streaming:
            console.print("Screen streaming already running", style="yellow")
            return

        self.screenshot_interval = interval
        self.save_frames = save_frames
        self.is_streaming = True

        def stream_worker():
            frame_count = 0
            while self.is_streaming:
                try:
                    # Take screenshot using Selenium
                    screenshot_data = self._capture_screenshot()
                    if screenshot_data:
                        self.latest_screenshot = screenshot_data

                        if self.save_frames:
                            # Save frame to disk
                            frame_file = self.output_dir / f"frame_{frame_count:06d}.png"
                            with open(frame_file, 'wb') as f:
                                f.write(base64.b64decode(screenshot_data))
                            frame_count += 1

                        # Create description of current screen
                        description = self._analyze_screenshot()
                        if description:
                            desc_file = self.output_dir / "current_screen.json"
                            with open(desc_file, 'w') as f:
                                json.dump({
                                    "timestamp": time.time(),
                                    "frame_count": frame_count,
                                    "description": description,
                                    "screenshot_base64": screenshot_data[:100] + "..." if len(screenshot_data) > 100 else screenshot_data
                                }, f, indent=2)

                    time.sleep(self.screenshot_interval)

                except Exception as e:
                    console.print(f"Streaming error: {e}", style="red")
                    time.sleep(1)

        self.stream_thread = threading.Thread(target=stream_worker, daemon=True)
        self.stream_thread.start()

        console.print(f"Screen streaming started (interval: {interval}s, save_frames: {save_frames})", style="green")

    def stop_streaming(self):
        """Stop screen streaming"""
        if not self.is_streaming:
            console.print("Screen streaming not running", style="yellow")
            return

        self.is_streaming = False
        if self.stream_thread:
            self.stream_thread.join(timeout=2)

        console.print("Screen streaming stopped", style="yellow")

    def get_current_screen(self):
        """Get current screen description"""
        if not self.latest_screenshot:
            return None

        desc_file = self.output_dir / "current_screen.json"
        if desc_file.exists():
            with open(desc_file, 'r') as f:
                return json.load(f)
        return None

    def _capture_screenshot(self):
        """Capture screenshot using Selenium"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            options = Options()
            options.add_experimental_option("debuggerAddress", f"localhost:{self.debug_port}")

            driver = webdriver.Chrome(options=options)
            screenshot_base64 = driver.get_screenshot_as_base64()
            driver.quit()

            return screenshot_base64

        except Exception as e:
            return None

    def _analyze_screenshot(self):
        """Analyze screenshot to create description"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            options = Options()
            options.add_experimental_option("debuggerAddress", f"localhost:{self.debug_port}")

            driver = webdriver.Chrome(options=options)

            # Get basic page info
            title = driver.title
            url = driver.current_url

            # Get visible elements info
            elements_info = driver.execute_script("""
                const elements = document.querySelectorAll('input, button, select, textarea, a[href], form');
                return Array.from(elements).slice(0, 20).map(el => ({
                    tag: el.tagName.toLowerCase(),
                    type: el.type || '',
                    name: el.name || '',
                    id: el.id || '',
                    text: el.textContent?.slice(0, 50) || '',
                    placeholder: el.placeholder || '',
                    visible: el.offsetParent !== null
                })).filter(el => el.visible);
            """)

            driver.quit()

            return {
                "title": title,
                "url": url,
                "visible_elements": elements_info,
                "element_count": len(elements_info)
            }

        except Exception as e:
            return {"error": str(e)}

# Global screen streamer instance
screen_streamer = ScreenStreamer()

class RemoteController:
    """Selenium-based remote controller for advanced Chrome automation"""

    def __init__(self, debug_port: int = 9222):
        self.debug_port = debug_port
        self.driver = None
        self.output_dir = Path("data")
        self.output_dir.mkdir(exist_ok=True)

    def connect(self):
        """Connect to Chrome using Selenium"""
        if not SELENIUM_AVAILABLE:
            console.print("Selenium not installed. Run: pip install selenium", style="red")
            return False

        try:
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", f"localhost:{self.debug_port}")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")

            self.driver = webdriver.Chrome(options=chrome_options)

            console.print("Connected to Chrome via Selenium", style="green")
            return True

        except Exception as e:
            console.print(f"Failed to connect via Selenium: {e}", style="red")
            return False

    def open_devtools(self):
        """Open Chrome DevTools"""
        try:
            self.driver.execute_script("window.open('chrome://inspect/#devices', '_blank');")
            # Switch to DevTools window
            windows = self.driver.window_handles
            if len(windows) > 1:
                self.driver.switch_to.window(windows[-1])
                console.print("DevTools opened", style="green")
                return True
            return False
        except Exception as e:
            console.print(f"Error opening DevTools: {e}", style="red")
            return False

    def get_console_logs(self):
        """Get console logs from browser"""
        try:
            logs = self.driver.get_log('browser')
            console_data = []

            for log in logs:
                console_data.append({
                    "timestamp": log['timestamp'],
                    "level": log['level'],
                    "message": log['message'],
                    "source": log.get('source', 'unknown')
                })

            return console_data
        except Exception as e:
            console.print(f"Error getting console logs: {e}", style="red")
            return []

    def get_network_logs(self):
        """Get network logs from browser"""
        try:
            logs = self.driver.get_log('performance')
            network_data = []

            for log in logs:
                message = json.loads(log['message'])
                if message['message']['method'].startswith('Network.'):
                    network_data.append({
                        "timestamp": log['timestamp'],
                        "method": message['message']['method'],
                        "params": message['message'].get('params', {})
                    })

            return network_data
        except Exception as e:
            console.print(f"Error getting network logs: {e}", style="red")
            return []

    def execute_js(self, script: str):
        """Execute JavaScript in current page"""
        try:
            result = self.driver.execute_script(script)
            return result
        except Exception as e:
            console.print(f"Error executing JavaScript: {e}", style="red")
            return None

    def navigate_to(self, url: str):
        """Navigate to URL"""
        try:
            self.driver.get(url)
            console.print(f"Navigated to: {url}", style="green")
            return True
        except Exception as e:
            console.print(f"Error navigating to {url}: {e}", style="red")
            return False

    def click_element(self, selector: str, by_type: str = "css"):
        """Click element by selector"""
        try:
            by_map = {
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH,
                "id": By.ID,
                "class": By.CLASS_NAME,
                "tag": By.TAG_NAME
            }

            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((by_map[by_type], selector))
            )
            element.click()
            console.print(f"Clicked element: {selector}", style="green")
            return True
        except Exception as e:
            console.print(f"Error clicking element {selector}: {e}", style="red")
            return False

    def type_text(self, selector: str, text: str, by_type: str = "css"):
        """Type text into element"""
        try:
            by_map = {
                "css": By.CSS_SELECTOR,
                "xpath": By.XPATH,
                "id": By.ID,
                "class": By.CLASS_NAME
            }

            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((by_map[by_type], selector))
            )
            element.clear()
            element.send_keys(text)
            console.print(f"Typed text into {selector}", style="green")
            return True
        except Exception as e:
            console.print(f"Error typing into {selector}: {e}", style="red")
            return False

    def get_page_source(self):
        """Get current page source"""
        try:
            return self.driver.page_source
        except Exception as e:
            console.print(f"Error getting page source: {e}", style="red")
            return ""

    def take_screenshot(self, filename: str = "screenshot"):
        """Take screenshot of current page"""
        try:
            filepath = self.output_dir / f"{filename}.png"
            self.driver.save_screenshot(str(filepath))
            console.print(f"Screenshot saved: {filepath}", style="green")
            return str(filepath)
        except Exception as e:
            console.print(f"Error taking screenshot: {e}", style="red")
            return None

    def close(self):
        """Close Selenium connection"""
        if self.driver:
            self.driver.quit()
            console.print("Selenium connection closed", style="yellow")

class WebDataExtractor:
    def __init__(self, debug_port: int = 9222):
        self.debug_port = debug_port
        self.websocket = None
        self.message_id = 0
        self.output_dir = Path("data")
        self.output_dir.mkdir(exist_ok=True)
        
    async def connect(self):
        """Connect to Chrome DevTools Protocol"""
        try:
            import requests
            response = requests.get(f"http://localhost:{self.debug_port}/json")
            tabs = response.json()
            
            if not tabs:
                raise Exception("No Chrome tabs found. Start Chrome with --remote-debugging-port")
            
            # Connect to first tab
            websocket_url = tabs[0]['webSocketDebuggerUrl']
            self.websocket = await websockets.connect(websocket_url)
            console.print(f"Connected to Chrome tab: {tabs[0]['title']}", style="green")
            return True
            
        except Exception as e:
            console.print(f"Failed to connect to Chrome: {e}", style="red")
            return False
    
    async def send_command(self, method: str, params: Dict = None) -> Dict:
        """Send command to Chrome DevTools"""
        if not self.websocket:
            raise Exception("Not connected to Chrome")
            
        self.message_id += 1
        message = {
            "id": self.message_id,
            "method": method,
            "params": params or {}
        }
        
        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        return json.loads(response)
    
    async def enable_domains(self):
        """Enable required Chrome DevTools domains"""
        domains = ["Runtime", "Network", "Page", "DOM", "Console", "Performance"]
        for domain in domains:
            await self.send_command(f"{domain}.enable")
        console.print("Enabled Chrome DevTools domains", style="green")
    
    async def capture_page_info(self) -> Dict:
        """Capture basic page information"""
        try:
            result = await self.send_command("Runtime.evaluate", {
                "expression": """({
                    title: document.title,
                    url: window.location.href,
                    timestamp: new Date().toISOString(),
                    viewport: {
                        width: window.innerWidth,
                        height: window.innerHeight
                    },
                    userAgent: navigator.userAgent
                })"""
            })
            
            return result.get("result", {}).get("value", {})
        except Exception as e:
            console.print(f"Error capturing page info: {e}", style="red")
            return {}
    
    async def capture_dom(self) -> Dict:
        """Capture DOM structure and content"""
        try:
            # Get document
            doc_result = await self.send_command("DOM.getDocument")
            root_node_id = doc_result["result"]["root"]["nodeId"]
            
            # Get outer HTML
            html_result = await self.send_command("DOM.getOuterHTML", {
                "nodeId": root_node_id
            })
            
            # Extract text content
            text_result = await self.send_command("Runtime.evaluate", {
                "expression": "document.body.innerText"
            })
            
            # Extract links
            links_result = await self.send_command("Runtime.evaluate", {
                "expression": """Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.textContent.trim(),
                    href: a.href,
                    title: a.title
                }))"""
            })
            
            # Extract images
            images_result = await self.send_command("Runtime.evaluate", {
                "expression": """Array.from(document.querySelectorAll('img[src]')).map(img => ({
                    src: img.src,
                    alt: img.alt,
                    title: img.title,
                    width: img.width,
                    height: img.height
                }))"""
            })
            
            return {
                "html": html_result.get("result", {}).get("value", ""),
                "text": text_result.get("result", {}).get("value", ""),
                "links": links_result.get("result", {}).get("value", []),
                "images": images_result.get("result", {}).get("value", [])
            }
            
        except Exception as e:
            console.print(f"Error capturing DOM: {e}", style="red")
            return {}
    
    async def capture_network(self) -> List[Dict]:
        """Capture network requests"""
        try:
            result = await self.send_command("Runtime.evaluate", {
                "expression": """({
                    resources: performance.getEntriesByType('resource').map(r => ({
                        name: r.name,
                        type: r.initiatorType,
                        size: r.transferSize,
                        duration: r.duration,
                        startTime: r.startTime
                    }))
                })"""
            })
            
            return result.get("result", {}).get("value", {}).get("resources", [])
            
        except Exception as e:
            console.print(f"Error capturing network: {e}", style="red")
            return []
    
    async def save_data(self, data: Dict, filename: str, format_type: str = "json"):
        """Save extracted data to file"""
        filepath = self.output_dir / f"{filename}.{format_type}"
        
        if format_type == "json":
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
        elif format_type == "md":
            markdown_content = self.convert_to_markdown(data)
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(markdown_content)
        
        console.print(f"Data saved to: {filepath}", style="green")
        return str(filepath)
    
    def convert_to_markdown(self, data: Dict) -> str:
        """Convert data to markdown format"""
        md_lines = []
        
        if "page_info" in data:
            info = data["page_info"]
            md_lines.extend([
                f"# {info.get('title', 'Untitled Page')}",
                f"**URL:** {info.get('url', '')}",
                f"**Timestamp:** {info.get('timestamp', '')}",
                f"**Viewport:** {info.get('viewport', {}).get('width', 0)}x{info.get('viewport', {}).get('height', 0)}",
                ""
            ])
        
        if "dom" in data and "text" in data["dom"]:
            md_lines.extend([
                "## Page Content",
                data["dom"]["text"][:5000] + ("..." if len(data["dom"]["text"]) > 5000 else ""),
                ""
            ])
        
        if "dom" in data and "links" in data["dom"]:
            md_lines.append("## Links")
            for link in data["dom"]["links"][:20]:  # Limit to first 20 links
                md_lines.append(f"- [{link.get('text', 'No text')}]({link.get('href', '')})")
            md_lines.append("")
        
        return "\n".join(md_lines)
    
    async def close(self):
        """Close connection"""
        if self.websocket:
            await self.websocket.close()


# CLI Commands
@click.group()
@click.version_option(version="1.0.0")
def cli():
    """WebData CLI - Web data extraction tool for AI assistants"""
    pass

@cli.command()
@click.option('--port', default=9222, help='Chrome debug port')
@click.option('--format', default='json', type=click.Choice(['json', 'md']), help='Output format')
@click.option('--output', default='page_data', help='Output filename (without extension)')
@click.option('--stream', is_flag=True, help='Stream output directly to terminal for AI reading')
def capture_page(port, format, output, stream):
    """Capture complete page data (DOM, text, links, images, network)"""
    async def _capture():
        extractor = WebDataExtractor(port)
        
        if not await extractor.connect():
            return
        
        try:
            await extractor.enable_domains()
            console.print("Capturing page data...", style="yellow")
            
            page_info = await extractor.capture_page_info()
            dom_data = await extractor.capture_dom()
            network_data = await extractor.capture_network()
            
            data = {
                "page_info": page_info,
                "dom": dom_data,
                "network": network_data,
                "extraction_timestamp": time.time()
            }

            if stream:
                # Stream directly to terminal for AI reading
                console.print("=== WEBDATA CAPTURE STREAM START ===", style="cyan")
                console.print(f"URL: {page_info.get('url', 'Unknown')}", style="dim")
                console.print(f"Title: {page_info.get('title', 'Unknown')}", style="dim")
                console.print("=== PAGE DATA START ===", style="cyan")

                # Output JSON data directly to terminal
                import json
                print(json.dumps(data, indent=2, ensure_ascii=False))

                console.print("=== PAGE DATA END ===", style="cyan")
                console.print("=== WEBDATA CAPTURE STREAM END ===", style="cyan")
            else:
                await extractor.save_data(data, output, format)
                console.print("Page data captured successfully", style="green")
            
        finally:
            await extractor.close()
    
    asyncio.run(_capture())

@cli.command()
@click.option('--port', default=9222, help='Chrome debug port')
@click.option('--format', default='json', type=click.Choice(['json', 'md']), help='Output format')
@click.option('--output', default='dom_data', help='Output filename (without extension)')
def get_dom(port, format, output):
    """Extract DOM structure and text content only"""
    async def _get_dom():
        extractor = WebDataExtractor(port)
        if not await extractor.connect():
            return
        
        try:
            await extractor.enable_domains()
            console.print("Extracting DOM...", style="yellow")
            
            page_info = await extractor.capture_page_info()
            dom_data = await extractor.capture_dom()
            
            data = {
                "page_info": page_info,
                "dom": dom_data,
                "extraction_timestamp": time.time()
            }
            
            await extractor.save_data(data, output, format)
            console.print("DOM extracted successfully", style="green")
            
        finally:
            await extractor.close()
    
    asyncio.run(_get_dom())

@cli.command()
@click.option('--port', default=9222, help='Chrome debug port')
@click.option('--output', default='network_data', help='Output filename (without extension)')
def get_network(port, output):
    """Extract network requests and performance data"""
    async def _get_network():
        extractor = WebDataExtractor(port)
        if not await extractor.connect():
            return
        
        try:
            await extractor.enable_domains()
            console.print("Extracting network data...", style="yellow")
            
            page_info = await extractor.capture_page_info()
            network_data = await extractor.capture_network()
            
            data = {
                "page_info": page_info,
                "network": network_data,
                "extraction_timestamp": time.time()
            }
            
            await extractor.save_data(data, output, "json")
            console.print("Network data extracted successfully", style="green")
            
        finally:
            await extractor.close()
    
    asyncio.run(_get_network())

@cli.command()
@click.option('--port', default=9222, help='Chrome debug port')
@click.option('--output', default='text_content', help='Output filename (without extension)')
@click.option('--stream', is_flag=True, help='Stream output directly to terminal for AI reading')
def get_text(port, output, stream):
    """Extract only text content from page (AI-optimized)"""
    async def _get_text():
        extractor = WebDataExtractor(port)
        if not await extractor.connect():
            return
        
        try:
            await extractor.enable_domains()
            console.print("Extracting text content...", style="yellow")
            
            # Get clean text content
            result = await extractor.send_command("Runtime.evaluate", {
                "expression": """({
                    title: document.title,
                    url: window.location.href,
                    text: document.body.innerText,
                    headings: Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6')).map(h => ({
                        level: h.tagName.toLowerCase(),
                        text: h.textContent.trim()
                    })),
                    paragraphs: Array.from(document.querySelectorAll('p')).map(p => p.textContent.trim()).filter(t => t.length > 0)
                })"""
            })
            
            data = result.get("result", {}).get("value", {})
            data["extraction_timestamp"] = time.time()

            if stream:
                # Stream directly to terminal for AI reading
                console.print("=== WEBDATA STREAM START ===", style="cyan")
                console.print(f"URL: {data.get('url', 'Unknown')}", style="dim")
                console.print(f"Title: {data.get('title', 'Unknown')}", style="dim")
                console.print(f"Content Length: {len(data.get('text', ''))} characters", style="dim")
                console.print("=== CONTENT START ===", style="cyan")

                # Output content directly to terminal
                print(data.get('text', ''))

                console.print("=== CONTENT END ===", style="cyan")
                console.print("=== WEBDATA STREAM END ===", style="cyan")
            else:
                # Save as both markdown and JSON (traditional mode)
                await extractor.save_data(data, output, "md")
                await extractor.save_data(data, output, "json")
                console.print("Text content extracted successfully", style="green")
            
        finally:
            await extractor.close()
    
    asyncio.run(_get_text())

@cli.command()
@click.option('--port', default=9222, help='Chrome debug port')
def list_tabs(port):
    """List all available Chrome tabs"""
    try:
        import requests
        response = requests.get(f"http://localhost:{port}/json")
        tabs = response.json()
        
        table = Table(title="Chrome Tabs")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("URL", style="blue")
        table.add_column("Type", style="yellow")
        
        for tab in tabs:
            table.add_row(
                tab.get("id", "")[:8],
                tab.get("title", "")[:50],
                tab.get("url", "")[:60],
                tab.get("type", "")
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"Error listing tabs: {e}", style="red")

def check_chrome_running(port=9222):
    """Check if Chrome is already running with debug port"""
    try:
        import requests
        response = requests.get(f"http://localhost:{port}/json", timeout=2)
        if response.status_code == 200:
            tabs = response.json()
            return True, len(tabs)
    except:
        pass
    return False, 0

def find_chrome_processes():
    """Find running Chrome processes"""
    try:
        if os.name == 'nt':  # Windows
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq chrome.exe'],
                                  capture_output=True, text=True)
            chrome_processes = [line for line in result.stdout.split('\n')
                              if 'chrome.exe' in line.lower()]
            return len(chrome_processes)
        else:  # Linux/Mac
            result = subprocess.run(['pgrep', '-f', 'chrome'],
                                  capture_output=True, text=True)
            return len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
    except:
        return 0

def enable_chrome_debugging(port=9222):
    """Try to enable debugging on existing Chrome instance"""
    try:
        if os.name == 'nt':  # Windows
            # Try to find Chrome processes and restart with debugging
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq chrome.exe', '/FO', 'CSV'],
                                  capture_output=True, text=True)
            if 'chrome.exe' in result.stdout:
                console.print("Found existing Chrome processes. Please close Chrome and try again,", style="yellow")
                console.print("or use --force-new to start a new instance.", style="yellow")
                return False
        return False
    except:
        return False

@cli.command()
@click.option('--profile', default='debug', help='Chrome profile name to use')
@click.option('--port', default=9222, help='Debug port')
@click.option('--reuse-existing', is_flag=True, help='Try to reuse existing Chrome instance (slower)')
def start_chrome(profile, port, reuse_existing):
    """Start Chrome with debugging enabled (default: new instance for optimal performance)"""
    try:
        if reuse_existing:
            # Check if Chrome is already running with debugging
            is_running, tab_count = check_chrome_running(port)

            if is_running:
                console.print(f"✅ Chrome already running with debugging on port {port}", style="green")
                console.print(f"Found {tab_count} tabs available", style="dim")
                console.print("You can use WebData commands immediately!", style="blue")
                return

            # Check for existing Chrome processes
            chrome_count = find_chrome_processes()
            if chrome_count > 0:
                console.print(f"⚠️  Found {chrome_count} Chrome processes running", style="yellow")
                console.print("Chrome may be running without debugging enabled.", style="yellow")
                console.print("Options:", style="cyan")
                console.print("  1. Close all Chrome windows and run this command again", style="dim")
                console.print("  2. Remove --reuse-existing to start a new Chrome instance", style="dim")
                console.print("  3. Manually start Chrome with: --remote-debugging-port=9222", style="dim")
                return
        # Find Chrome executable
        chrome_paths = [
            "chrome",
            "google-chrome",
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]

        chrome_exe = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_exe = path
                break
            else:
                try:
                    subprocess.run([path, "--version"], capture_output=True, check=True)
                    chrome_exe = path
                    break
                except:
                    continue

        if not chrome_exe:
            console.print("Chrome executable not found", style="red")
            console.print("Please install Chrome or add it to PATH", style="yellow")
            return

        # Create user data directory
        if os.name == 'nt':  # Windows
            user_data_dir = f"C:\\temp\\chrome_{profile}"
        else:
            user_data_dir = f"/tmp/chrome_{profile}"

        chrome_cmd = [
            chrome_exe,
            f"--remote-debugging-port={port}",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check"
        ]

        if reuse_existing:
            console.print(f"🔄 Trying to reuse existing Chrome with profile: {profile}", style="yellow")
        else:
            console.print(f"🚀 Starting NEW Chrome instance with profile: {profile} (optimal)", style="yellow")

        subprocess.Popen(chrome_cmd)

        # Wait a moment and check if it started successfully
        time.sleep(2)
        is_running, tab_count = check_chrome_running(port)

        if is_running:
            console.print(f"✅ Chrome started successfully on port {port}", style="green")
            console.print(f"Found {tab_count} tabs available", style="dim")
            console.print("You can now use WebData commands!", style="blue")
        else:
            console.print(f"⚠️  Chrome started but debugging may not be enabled", style="yellow")
            console.print("Please open a webpage in Chrome, then use other commands", style="blue")
        console.print("Please open a webpage in Chrome, then use other commands", style="blue")

    except Exception as e:
        console.print(f"Error starting Chrome: {e}", style="red")
        console.print("Try starting Chrome manually with:", style="yellow")
        console.print(f"chrome --remote-debugging-port={port} --user-data-dir=C:\\temp\\chrome_debug", style="cyan")

@cli.command()
@click.option('--port', default=9222, help='Debug port to check')
def check_chrome(port):
    """Check Chrome debugging status"""
    try:
        # Check if Chrome debugging is available
        is_running, tab_count = check_chrome_running(port)

        if is_running:
            console.print(f"✅ Chrome debugging is ACTIVE on port {port}", style="green")
            console.print(f"📑 Found {tab_count} tabs available", style="dim")

            # Get tabs info
            import requests
            response = requests.get(f"http://localhost:{port}/json")
            tabs = response.json()

            if tabs:
                console.print("\n🌐 Available tabs:", style="cyan")
                for i, tab in enumerate(tabs[:5]):  # Show first 5 tabs
                    title = tab.get('title', 'No title')[:50]
                    url = tab.get('url', 'No URL')[:60]
                    console.print(f"  {i+1}. {title}", style="white")
                    console.print(f"     {url}", style="dim")

                if len(tabs) > 5:
                    console.print(f"     ... and {len(tabs) - 5} more tabs", style="dim")
        else:
            console.print(f"❌ Chrome debugging is NOT available on port {port}", style="red")

            # Check for Chrome processes
            chrome_count = find_chrome_processes()
            if chrome_count > 0:
                console.print(f"⚠️  Found {chrome_count} Chrome processes running", style="yellow")
                console.print("Chrome may be running without debugging enabled.", style="yellow")
                console.print("\n💡 Solutions:", style="cyan")
                console.print("  1. Close Chrome and run: webdata start-chrome", style="dim")
                console.print("  2. Start Chrome manually with debugging:", style="dim")
                console.print(f"     chrome --remote-debugging-port={port}", style="dim")
            else:
                console.print("No Chrome processes found.", style="yellow")
                console.print("Run: webdata start-chrome", style="cyan")

    except Exception as e:
        console.print(f"Error checking Chrome: {e}", style="red")

@cli.command()
@click.option('--project-path', default='.', help='Path to project directory')
def integrate(project_path):
    """Copy integration guide to project directory"""
    try:
        project_dir = Path(project_path)
        if not project_dir.exists():
            console.print(f"Project directory does not exist: {project_path}", style="red")
            return

        # Find the integration guide
        guide_file = None
        search_paths = [
            Path("AI_INTEGRATION_GUIDE.md"),
            Path(__file__).parent / "AI_INTEGRATION_GUIDE.md",
            Path.home() / ".local" / "share" / "webdata-cli" / "AI_INTEGRATION_GUIDE.md"
        ]

        for path in search_paths:
            if path.exists():
                guide_file = path
                break

        if not guide_file:
            console.print("Integration guide not found", style="red")
            return

        # Copy to project
        target_file = project_dir / "AI_INTEGRATION_GUIDE.md"
        shutil.copy2(guide_file, target_file)

        # Create data directory for screenshots
        data_dir = project_dir / "data"
        data_dir.mkdir(exist_ok=True)

        # Update guide content with fixed paths
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace relative paths with project-specific paths
        content = content.replace('data/current-interface.jpg', str(data_dir / 'current-interface.jpg'))

        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(content)

        console.print(f"Integration guide copied to: {target_file}", style="green")
        console.print(f"Data directory created: {data_dir}", style="green")
        console.print("AI assistants can now reference AI_INTEGRATION_GUIDE.md for usage instructions", style="blue")

    except Exception as e:
        console.print(f"Error integrating: {e}", style="red")

@cli.command()
@click.option('--all', is_flag=True, help='Clean all data including logs')
@click.option('--older-than', default=0, help='Clean files older than N hours (0 = all files)')
@click.option('--auto', is_flag=True, help='Use auto-cleanup configuration')
def cleanup(all, older_than, auto):
    """Clean extracted data files to prevent overflow"""
    try:
        if auto:
            # Use auto-cleanup configuration
            auto_cleaner.auto_cleanup()
            return

        data_dir = Path("data")
        logs_dir = Path("logs")

        if not data_dir.exists() and not logs_dir.exists():
            console.print("No data directories found", style="yellow")
            return

        import time
        current_time = time.time()
        cutoff_time = current_time - (older_than * 3600)  # Convert hours to seconds

        cleaned_files = []
        total_size = 0

        # Clean data directory
        if data_dir.exists():
            for file_path in data_dir.iterdir():
                if file_path.is_file():
                    file_time = file_path.stat().st_mtime
                    if older_than == 0 or file_time < cutoff_time:
                        file_size = file_path.stat().st_size
                        total_size += file_size
                        file_path.unlink()
                        cleaned_files.append(f"data/{file_path.name}")

        # Clean logs directory if --all flag is used
        if all and logs_dir.exists():
            for file_path in logs_dir.iterdir():
                if file_path.is_file():
                    file_time = file_path.stat().st_mtime
                    if older_than == 0 or file_time < cutoff_time:
                        file_size = file_path.stat().st_size
                        total_size += file_size
                        file_path.unlink()
                        cleaned_files.append(f"logs/{file_path.name}")

        if cleaned_files:
            console.print(f"Cleaned {len(cleaned_files)} files ({total_size:,} bytes)", style="green")
            for file in cleaned_files[:10]:  # Show first 10 files
                console.print(f"  - {file}", style="dim")
            if len(cleaned_files) > 10:
                console.print(f"  ... and {len(cleaned_files) - 10} more files", style="dim")
        else:
            console.print("No files to clean", style="yellow")

    except Exception as e:
        console.print(f"Error during cleanup: {e}", style="red")

# Remote Control Commands
@cli.command()
@click.option('--port', default=9222, help='Chrome debug port')
@click.option('--output', help='Save result to file')
@click.option('--timeout', default=10, help='Timeout in seconds')
@click.option('--stream', is_flag=True, help='Stream result directly to terminal for AI reading')
@click.option('--auto-capture', is_flag=True, default=True, help='Auto-capture interface state and screenshot on page load')
@click.argument('selenium_command', nargs=-1, required=True)
def remote(port, output, timeout, selenium_command, stream, auto_capture):
    """Execute Selenium commands on Chrome browser

    Examples:
        webdata remote get "https://example.com"
        webdata remote find_element "By.ID, 'button'" click
        webdata remote execute_script "return document.title"
        webdata remote get_log "browser"
        webdata remote save_screenshot "screenshot.png"
    """
    if not SELENIUM_AVAILABLE:
        console.print("Selenium not installed. Install with: pip install selenium", style="red")
        return

    controller = RemoteController(port)
    if not controller.connect():
        console.print("Failed to connect to Chrome", style="red")
        return

    try:
        # Parse and execute selenium command
        cmd_str = ' '.join(selenium_command)
        console.print(f"Executing: {cmd_str}", style="yellow")

        result = execute_selenium_command(controller.driver, cmd_str, timeout, auto_capture)

        if stream:
            # Stream result directly to terminal for AI reading
            console.print("=== WEBDATA REMOTE STREAM START ===", style="cyan")
            console.print(f"Command: {cmd_str}", style="dim")
            console.print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
            console.print("=== RESULT START ===", style="cyan")

            # Output result directly to terminal
            if result is not None:
                if isinstance(result, (dict, list)):
                    import json
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                else:
                    print(str(result))
            else:
                print("No result")

            console.print("=== RESULT END ===", style="cyan")
            console.print("=== WEBDATA REMOTE STREAM END ===", style="cyan")
        elif output:
            # Save result to file
            data = {
                "command": cmd_str,
                "result": str(result) if result is not None else None,
                "timestamp": time.time()
            }
            filepath = controller.output_dir / f"{output}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            console.print(f"Result saved to: {filepath}", style="green")
        else:
            console.print(f"Result: {result}", style="blue")

    except Exception as e:
        console.print(f"Error executing command: {e}", style="red")
    finally:
        controller.close()


def execute_selenium_command(driver, command: str, timeout: int = 10, auto_capture: bool = True):
    """Execute a Selenium command string"""
    try:
        # Parse command
        parts = command.split()
        if not parts:
            return None

        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        # Common Selenium commands
        if cmd == "get":
            url = args[0] if args else ""
            driver.get(url)

            # Auto-capture interface state after page load (if enabled)
            if auto_capture:
                try:
                    # Wait for page to load
                    import time
                    time.sleep(2)

                    # Capture interface state
                    interface_state = driver.execute_script("""
                    return {
                        url: window.location.href,
                        title: document.title,
                        readyState: document.readyState,
                        forms: Array.from(document.forms).map(f => ({
                            id: f.id,
                            action: f.action,
                            method: f.method,
                            inputs: Array.from(f.querySelectorAll('input')).map(i => ({
                                name: i.name,
                                type: i.type,
                                placeholder: i.placeholder,
                                required: i.required
                            }))
                        })),
                        buttons: Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"]')).map(b => ({
                            text: b.textContent || b.value,
                            type: b.type,
                            id: b.id,
                            className: b.className
                        })),
                        links: Array.from(document.querySelectorAll('a[href]')).slice(0, 10).map(a => ({
                            text: a.textContent.trim(),
                            href: a.href
                        })),
                        errors: Array.from(document.querySelectorAll('.error, .alert, .warning, [role="alert"]')).map(e => e.textContent.trim()),
                        pageText: document.body.innerText.slice(0, 500)
                    };
                    """)

                    # Take screenshot (fixed filename, lighter format)
                    from pathlib import Path
                    data_dir = Path("data")
                    data_dir.mkdir(exist_ok=True)

                    screenshot_path = data_dir / "current-interface.png"
                    driver.save_screenshot(str(screenshot_path))

                    # Convert to JPEG for smaller size
                    try:
                        from PIL import Image
                        img = Image.open(screenshot_path)
                        jpeg_path = data_dir / "current-interface.jpg"
                        img.convert('RGB').save(jpeg_path, 'JPEG', quality=85, optimize=True)
                        screenshot_path = jpeg_path
                        # Remove PNG file
                        (data_dir / "current-interface.png").unlink()
                    except ImportError:
                        pass  # Keep PNG if PIL not available

                    # Return comprehensive result
                    result = {
                        "navigation": f"Navigated to: {url}",
                        "screenshot": str(screenshot_path),
                        "interface_state": interface_state
                    }

                    return result

                except Exception as e:
                    return f"Navigated to: {url} (auto-capture failed: {e})"
            else:
                return f"Navigated to: {url}"

        elif cmd == "current_url":
            return driver.current_url

        elif cmd == "title":
            return driver.title

        elif cmd == "page_source":
            return driver.page_source[:1000] + "..." if len(driver.page_source) > 1000 else driver.page_source

        elif cmd == "execute_script":
            script = ' '.join(args)
            result = driver.execute_script(script)
            return result

        elif cmd == "find_element":
            # Parse: find_element "By.ID, 'element_id'"
            if args:
                by_and_value = ' '.join(args).strip('"\'')
                if ',' in by_and_value:
                    by_part, value_part = by_and_value.split(',', 1)
                    by_part = by_part.strip()
                    value_part = value_part.strip().strip('"\'')

                    # Map string to By constants
                    by_map = {
                        "By.ID": By.ID,
                        "By.CLASS_NAME": By.CLASS_NAME,
                        "By.CSS_SELECTOR": By.CSS_SELECTOR,
                        "By.XPATH": By.XPATH,
                        "By.TAG_NAME": By.TAG_NAME,
                        "By.NAME": By.NAME
                    }

                    if by_part in by_map:
                        element = driver.find_element(by_map[by_part], value_part)
                        return f"Found element: {element.tag_name}"
            return "Invalid find_element syntax"

        elif cmd == "click":
            # Assume last find_element result or use CSS selector
            if args:
                selector = args[0].strip('"\'')
                element = driver.find_element(By.CSS_SELECTOR, selector)
                element.click()
                return f"Clicked element: {selector}"
            return "No selector provided"

        elif cmd == "send_keys":
            if len(args) >= 2:
                selector = args[0].strip('"\'')
                text = ' '.join(args[1:]).strip('"\'')
                element = driver.find_element(By.CSS_SELECTOR, selector)
                element.send_keys(text)
                return f"Typed '{text}' into {selector}"
            return "Invalid send_keys syntax"

        elif cmd == "get_log":
            log_type = args[0] if args else "browser"
            logs = driver.get_log(log_type)
            return logs[:10]  # Return first 10 log entries

        elif cmd == "save_screenshot":
            filename = args[0] if args else "screenshot.png"
            filepath = Path("data") / filename
            driver.save_screenshot(str(filepath))
            return f"Screenshot saved: {filepath}"

        elif cmd == "window_size":
            return driver.get_window_size()

        elif cmd == "back":
            driver.back()
            return "Navigated back"

        elif cmd == "forward":
            driver.forward()
            return "Navigated forward"

        elif cmd == "refresh":
            driver.refresh()
            return "Page refreshed"

        elif cmd == "close":
            driver.close()
            return "Window closed"

        elif cmd == "scroll_to_bottom":
            # Smart scroll to bottom with checks
            script = """
            var totalHeight = 0;
            var distance = 100;
            var timer = setInterval(function() {
                var scrollHeight = document.body.scrollHeight;
                window.scrollBy(0, distance);
                totalHeight += distance;

                if(totalHeight >= scrollHeight){
                    clearInterval(timer);
                }
            }, 100);

            // Return current scroll info
            return {
                scrollHeight: document.body.scrollHeight,
                clientHeight: window.innerHeight,
                canScroll: document.body.scrollHeight > window.innerHeight
            };
            """
            return driver.execute_script(script)

        elif cmd == "scroll_info":
            # Get scroll information
            script = """
            return {
                scrollTop: window.pageYOffset,
                scrollHeight: document.body.scrollHeight,
                clientHeight: window.innerHeight,
                canScroll: document.body.scrollHeight > window.innerHeight,
                atBottom: (window.innerHeight + window.pageYOffset) >= document.body.scrollHeight
            };
            """
            return driver.execute_script(script)

        elif cmd == "wait_for_load":
            # Wait for page to fully load
            timeout = int(args[0]) if args else 10
            script = "return document.readyState === 'complete'"

            import time
            start_time = time.time()
            while time.time() - start_time < timeout:
                if driver.execute_script(script):
                    return f"Page loaded in {time.time() - start_time:.2f} seconds"
                time.sleep(0.5)
            return f"Page load timeout after {timeout} seconds"

        elif cmd == "smart_scroll":
            # Smart scroll with content detection
            amount = int(args[0]) if args else 1000
            script = f"""
            var scrollInfo = {{
                before: window.pageYOffset,
                scrollHeight: document.body.scrollHeight,
                canScroll: document.body.scrollHeight > window.innerHeight
            }};

            if (scrollInfo.canScroll) {{
                window.scrollBy(0, {amount});
                scrollInfo.after = window.pageYOffset;
                scrollInfo.scrolled = scrollInfo.after > scrollInfo.before;
            }} else {{
                scrollInfo.after = scrollInfo.before;
                scrollInfo.scrolled = false;
                scrollInfo.message = "Page too short to scroll";
            }}

            return scrollInfo;
            """
            return driver.execute_script(script)

        else:
            # Try to execute as raw Python code on driver
            try:
                result = eval(f"driver.{command}")
                return result
            except:
                return f"Unknown command: {cmd}. Try: get, title, execute_script, scroll_info, smart_scroll, etc."

    except Exception as e:
        return f"Error: {str(e)}"



@cli.command()
def uninstall():
    """Uninstall WebData CLI and clean up all data"""
    try:
        import subprocess
        import sys
        from pathlib import Path

        console.print("🗑️  Uninstalling WebData CLI...", style="yellow")

        # Confirm with user
        confirm = click.confirm("This will remove WebData CLI and all data. Continue?")
        if not confirm:
            console.print("Uninstall cancelled.", style="blue")
            return

        # Clean up data directories
        cleanup_dirs = [
            Path("data"),
            Path("logs"),
            Path.home() / ".webdata",
            Path.home() / ".local" / "share" / "webdata-cli"
        ]

        for dir_path in cleanup_dirs:
            if dir_path.exists():
                import shutil
                shutil.rmtree(dir_path)
                console.print(f"Removed: {dir_path}", style="dim")

        # Remove package
        console.print("Removing package...", style="yellow")
        result = subprocess.run([
            sys.executable, "-m", "pip", "uninstall", "webdata-cli", "-y"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            console.print("✅ WebData CLI uninstalled successfully!", style="green")
            console.print("All data and configurations have been removed.", style="dim")
        else:
            console.print("❌ Failed to uninstall package:", style="red")
            console.print(result.stderr, style="red")

    except Exception as e:
        console.print(f"Error during uninstall: {e}", style="red")

@cli.command()
def status():
    """Show current data usage and statistics"""
    try:
        data_dir = Path("data")
        logs_dir = Path("logs")

        table = Table(title="WebData CLI Status")
        table.add_column("Directory", style="cyan")
        table.add_column("Files", style="green")
        table.add_column("Size", style="yellow")
        table.add_column("Latest File", style="blue")

        for dir_path, dir_name in [(data_dir, "data"), (logs_dir, "logs")]:
            if dir_path.exists():
                files = list(dir_path.iterdir())
                file_count = len([f for f in files if f.is_file()])
                total_size = sum(f.stat().st_size for f in files if f.is_file())

                # Find latest file
                latest_file = "None"
                if files:
                    latest = max((f for f in files if f.is_file()),
                               key=lambda x: x.stat().st_mtime, default=None)
                    if latest:
                        latest_file = latest.name

                # Format size
                if total_size < 1024:
                    size_str = f"{total_size} B"
                elif total_size < 1024 * 1024:
                    size_str = f"{total_size / 1024:.1f} KB"
                else:
                    size_str = f"{total_size / (1024 * 1024):.1f} MB"

                table.add_row(dir_name, str(file_count), size_str, latest_file)
            else:
                table.add_row(dir_name, "0", "0 B", "None")

        console.print(table)

        # Show cleanup recommendations
        data_files = list(data_dir.iterdir()) if data_dir.exists() else []
        if len(data_files) > 20:
            console.print("\n💡 Recommendation: Consider running 'webdata cleanup' to clean old files", style="yellow")
        elif len(data_files) > 50:
            console.print("\n⚠️  Warning: Many files detected. Run 'webdata cleanup' to prevent overflow", style="red")

    except Exception as e:
        console.print(f"Error checking status: {e}", style="red")

@cli.group()
def autoclean():
    """Auto-cleanup management commands"""
    pass

@autoclean.command()
def start():
    """Start auto-cleanup scheduler"""
    auto_cleaner.start_scheduler()

@autoclean.command()
def stop():
    """Stop auto-cleanup scheduler"""
    auto_cleaner.stop_scheduler()

@autoclean.command()
def status():
    """Show auto-cleanup configuration and status"""
    config = auto_cleaner.load_config()

    table = Table(title="Auto-Cleanup Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Enabled", str(config["auto_cleanup_enabled"]))
    table.add_row("Interval (hours)", str(config["cleanup_interval_hours"]))
    table.add_row("Max file age (hours)", str(config["max_file_age_hours"]))
    table.add_row("Max files count", str(config["max_files_count"]))
    table.add_row("Max total size (MB)", str(config["max_total_size_mb"]))
    table.add_row("Scheduler running", str(auto_cleaner.is_running))

    console.print(table)

@autoclean.command()
@click.option('--enabled/--disabled', default=True, help='Enable/disable auto-cleanup')
@click.option('--interval', default=24, help='Cleanup interval in hours')
@click.option('--max-age', default=48, help='Maximum file age in hours')
@click.option('--max-files', default=100, help='Maximum number of files to keep')
@click.option('--max-size', default=100, help='Maximum total size in MB')
def config(enabled, interval, max_age, max_files, max_size):
    """Configure auto-cleanup settings"""
    config = {
        "auto_cleanup_enabled": enabled,
        "cleanup_interval_hours": interval,
        "max_file_age_hours": max_age,
        "max_files_count": max_files,
        "max_total_size_mb": max_size
    }

    auto_cleaner.save_config(config)
    console.print("Auto-cleanup configuration updated", style="green")

    # Restart scheduler if it was running
    if auto_cleaner.is_running:
        auto_cleaner.stop_scheduler()
        if enabled:
            auto_cleaner.start_scheduler()

@autoclean.command()
def run():
    """Run cleanup now using auto-cleanup configuration"""
    auto_cleaner.auto_cleanup()

@autoclean.command()
def logs():
    """Show auto-cleanup logs"""
    log_file = Path("logs/auto_cleanup.log")
    if log_file.exists():
        with open(log_file, 'r') as f:
            lines = f.readlines()
            for line in lines[-20:]:  # Show last 20 lines
                console.print(line.strip(), style="dim")
    else:
        console.print("No auto-cleanup logs found", style="yellow")

@cli.group()
def stream():
    """Screen streaming commands for real-time Chrome monitoring"""
    pass

@stream.command()
@click.option('--interval', default=1.0, help='Screenshot interval in seconds')
@click.option('--save-frames', is_flag=True, help='Save frames to disk')
def start(interval, save_frames):
    """Start real-time screen streaming"""
    screen_streamer.start_streaming(interval, save_frames)

@stream.command()
def stop():
    """Stop screen streaming"""
    screen_streamer.stop_streaming()

@stream.command()
def status():
    """Show streaming status"""
    if screen_streamer.is_streaming:
        console.print("✅ Screen streaming is ACTIVE", style="green")
        console.print(f"   Interval: {screen_streamer.screenshot_interval}s", style="dim")
        console.print(f"   Save frames: {screen_streamer.save_frames}", style="dim")
    else:
        console.print("❌ Screen streaming is INACTIVE", style="red")

@stream.command()
def current():
    """Get current screen description"""
    screen_info = screen_streamer.get_current_screen()
    if screen_info:
        console.print("📺 Current Screen Info:", style="cyan")
        console.print(f"   Title: {screen_info['description']['title']}", style="white")
        console.print(f"   URL: {screen_info['description']['url']}", style="dim")
        console.print(f"   Elements: {screen_info['description']['element_count']} visible", style="dim")
        console.print(f"   Last update: {time.strftime('%H:%M:%S', time.localtime(screen_info['timestamp']))}", style="dim")

        # Show some visible elements
        elements = screen_info['description'].get('visible_elements', [])
        if elements:
            console.print("\n🎯 Visible Interactive Elements:", style="yellow")
            for i, el in enumerate(elements[:5]):  # Show first 5
                element_desc = f"{el['tag']}"
                if el['type']:
                    element_desc += f"[{el['type']}]"
                if el['name']:
                    element_desc += f" name='{el['name']}'"
                if el['text']:
                    element_desc += f" text='{el['text'][:30]}...'"
                console.print(f"   {i+1}. {element_desc}", style="dim")
    else:
        console.print("No screen info available. Start streaming first.", style="yellow")

@stream.command()
@click.option('--output', default='current_screen_analysis', help='Output file name')
def analyze(output):
    """Analyze current screen and save detailed info"""
    screen_info = screen_streamer.get_current_screen()
    if screen_info:
        output_file = Path("data") / f"{output}.json"
        Path("data").mkdir(exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(screen_info, f, indent=2)

        console.print(f"Screen analysis saved to: {output_file}", style="green")
    else:
        console.print("No screen info available. Start streaming first.", style="yellow")

def main():
    """Main entry point"""
    # Start auto-cleanup scheduler on startup if enabled
    config = auto_cleaner.load_config()
    if config.get("auto_cleanup_enabled", True):
        try:
            auto_cleaner.start_scheduler()
        except:
            pass  # Fail silently if scheduler can't start

    cli()

if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
云端版POM价格爬虫 - 使用Playwright
适配GitHub Actions环境
"""

import json
import os
import re
import requests
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# 配置
DATA_URL = "https://dc.oilchem.net/page/#/list?varietiesId=415&name=POM&businessType=2"
USERNAME = "hdgs"
PASSWORD = "hdgs888"
DATA_FILE = Path("data/prices.json")
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")


def scrape_prices():
    """使用Playwright抓取价格数据"""
    records = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            print("访问页面...")
            page.goto(DATA_URL, timeout=60000)
            page.wait_for_timeout(5000)
            
            # 检查是否需要登录
            if "请登录" in page.content():
                print("执行登录...")
                try:
                    # 点击登录按钮
                    page.click('text=点我登录')
                    page.wait_for_timeout(2000)
                    
                    # 填写登录信息
                    page.fill('#dialogUsername', USERNAME)
                    page.fill('#dialogPassword', PASSWORD)
                    page.click('button:has-text("登录")')
                    page.wait_for_timeout(8000)
                    
                    # 刷新页面
                    page.goto(DATA_URL, timeout=60000)
                    page.wait_for_timeout(5000)
                except Exception as e:
                    print(f"登录失败: {e}")
            
            # 提取表格数据
            print("提取数据...")
            table_data = page.evaluate('''() => {
                const tables = document.querySelectorAll('table');
                for (const table of tables) {
                    const text = table.textContent;
                    if (!text.includes('生产企业') || !text.includes('规格')) continue;
                    
                    const rows = table.querySelectorAll('tr');
                    const result = [];
                    let currentRegion = '';
                    let dateColumns = [];
                    
                    for (const row of rows) {
                        const cells = row.querySelectorAll('td, th');
                        if (cells.length === 0) continue;
                        
                        const firstCell = cells[0].textContent.trim();
                        
                        // 地区行
                        if (firstCell.includes('地区') || 
                            ['东北地区', '国外', '华北地区', '华东地区', '华中地区', '西北地区', '西南地区'].includes(firstCell)) {
                            currentRegion = firstCell;
                            continue;
                        }
                        
                        // 表头行
                        if (firstCell === '生产企业') {
                            dateColumns = [];
                            for (let i = 2; i < cells.length; i++) {
                                const match = cells[i].textContent.match(/\\d{4}\\/\\d{2}\\/\\d{2}/);
                                if (match) {
                                    dateColumns.push({index: i, date: match[0]});
                                }
                            }
                            continue;
                        }
                        
                        // 数据行
                        if (dateColumns.length > 0 && cells.length >= 3) {
                            const brand = firstCell;
                            const spec = cells[1].textContent.trim();
                            
                            if (!brand || !spec || brand === '生产企业') continue;
                            
                            for (const dc of dateColumns) {
                                const priceText = cells[dc.index]?.textContent?.trim() || '';
                                if (!priceText || priceText === '请登录' || priceText === '-') continue;
                                
                                const numMatch = priceText.match(/(\\d+)/);
                                if (!numMatch) continue;
                                
                                const price = parseInt(numMatch[1]);
                                if (price < 100) continue;
                                
                                result.push({
                                    brand: brand,
                                    specification: spec,
                                    region: currentRegion,
                                    price_date: dc.date,
                                    price_avg: price
                                });
                            }
                        }
                    }
                    
                    return result;
                }
                return [];
            }''')
            
            records = table_data
            print(f"提取到 {len(records)} 条记录")
            
        except Exception as e:
            print(f"抓取失败: {e}")
        finally:
            browser.close()
    
    return records


def save_data(records):
    """保存数据到JSON文件"""
    DATA_FILE.parent.mkdir(exist_ok=True)
    
    # 读取现有数据
    existing = []
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    
    # 合并数据（去重）
    existing_keys = {(r['brand'], r['specification'], r['price_date']) for r in existing}
    for r in records:
        key = (r['brand'], r['specification'], r['price_date'])
        if key not in existing_keys:
            existing.append(r)
            existing_keys.add(key)
    
    # 保存
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print(f"保存 {len(existing)} 条记录到 {DATA_FILE}")


def send_feishu_notification(records):
    """发送飞书通知"""
    if not FEISHU_WEBHOOK:
        print("未配置飞书Webhook，跳过通知")
        return
    
    if not records:
        return
    
    # 获取最新日期
    dates = sorted(set(r['price_date'] for r in records))
    latest_date = dates[-1] if dates else ''
    
    # 统计
    latest_records = [r for r in records if r['price_date'] == latest_date]
    specs = sorted(set(r['specification'] for r in latest_records))
    brands = sorted(set(r['brand'] for r in latest_records))
    
    # 构建消息
    message = f"""📊 POM价格日报 - {latest_date}

监控企业: {len(brands)}家
规格数量: {len(specs)}种

最新价格:
"""
    for spec in specs[:5]:  # 最多显示5个规格
        spec_records = [r for r in latest_records if r['specification'] == spec]
        prices = [f"{r['brand']}:{r['price_avg']}" for r in spec_records[:3]]
        message += f"\n【{spec}】{', '.join(prices)}"
    
    message += "\n\n💡 完整数据请访问仪表盘"
    
    # 发送
    try:
        response = requests.post(
            FEISHU_WEBHOOK,
            json={"msg_type": "text", "content": {"text": message}},
            timeout=10
        )
        print(f"飞书通知: {response.status_code}")
    except Exception as e:
        print(f"飞书通知失败: {e}")


def main():
    print("=" * 50)
    print("POM价格云端爬虫")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    # 抓取数据
    records = scrape_prices()
    
    if records:
        # 保存数据
        save_data(records)
        
        # 发送通知
        send_feishu_notification(records)
        
        print("\n✓ 完成!")
    else:
        print("\n✗ 未获取到数据")


if __name__ == '__main__':
    main()

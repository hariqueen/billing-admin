import os
import glob
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import time
from bs4 import BeautifulSoup

# 설정
PASSWORD = "1208192287"
INPUT_FOLDER = "/Users/haribo/Downloads/고지서"
OUTPUT_FOLDER = "추출된_텍스트"

def setup_driver():
    """Chrome 드라이버 설정"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    try:
        return webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"Chrome 드라이버 설정 실패: {e}")
        return None

def unlock_and_extract_html(file_path, driver):
    """HTML 파일의 비밀번호를 해제하고 텍스트를 추출"""
    try:
        file_url = f"file://{os.path.abspath(file_path)}"
        driver.get(file_url)
        time.sleep(1)  # 2초 → 1초로 단축
        
        # 비밀번호 필드 확인
        password_field = None
        try:
            password_field = WebDriverWait(driver, 2).until(  # 3초 → 2초로 단축
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
            )
        except TimeoutException:
            pass
        
        if password_field:
            password_field.clear()
            password_field.send_keys(PASSWORD)
            
            # 확인 버튼 클릭
            try:
                button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                button.click()
            except:
                password_field.send_keys("\n")
            
            time.sleep(2)  # 3초 → 2초로 단축
        
        # 텍스트 추출
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text, password_field is not None
        
    except Exception as e:
        print(f"파일 처리 중 오류: {os.path.basename(file_path)} - {e}")
        return None, False

def parse_billing_info(text_content):
    """텍스트에서 고객명과 금액을 추출"""
    # 고객명 매핑 (디버깅에서 확인된 패턴들)
    customer_mapping = {
        r'(\(주\)메타엠_구쁘)\s+고객님\s+([0-9,]+원)': '구쁘',
        r'(㈜메타엠\s+W컨셉)\s+고객님\s+([0-9,]+원)': 'W컨셉', 
        r'(메타엠_SAAS_디싸이더스)\s+고객님\s+([0-9,]+원)': '디싸이더스/애드프로젝트',
        r'(\(주\)메타엠_SAAS_9)\s+고객님\s+([0-9,]+원)': '매스프레소(콴다)',
        r'(\(주\)메타엠_앤하우스\(SAC2-S\))\s+고객님\s+([0-9,]+원)': '앤하우스',
        r'(\(주\)메타엠)\s+고객님\s+([0-9,]+원)': 'SK일렉링크',
    }
    
    customers = []
    amounts = []
    
    for pattern, mapped_name in customer_mapping.items():
        matches = re.findall(pattern, text_content, re.IGNORECASE)
        for match in matches:
            customers.append(mapped_name)
            amounts.append(match[1].strip())
    
    return customers, amounts

def process_html_files():
    """HTML 파일 처리"""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    html_files = glob.glob(os.path.join(INPUT_FOLDER, "*.html"))
    if not html_files:
        print(f"'{INPUT_FOLDER}' 폴더에서 HTML 파일을 찾을 수 없습니다.")
        return
    
    print(f"발견된 HTML 파일: {len(html_files)}개")
    
    driver = setup_driver()
    if not driver:
        return
    
    try:
        processed_count = 0
        unlocked_count = 0
        all_customers = []
        all_amounts = []
        file_results = {}
        
        for html_file in html_files:
            print(f"\n처리 중: {os.path.basename(html_file)}")
            
            text_content, was_locked = unlock_and_extract_html(html_file, driver)
            
            if text_content:
                base_name = os.path.splitext(os.path.basename(html_file))[0]
                output_file = os.path.join(OUTPUT_FOLDER, f"{base_name}.txt")
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                
                print(f"텍스트 추출 완료: {base_name}.txt")
                processed_count += 1
                
                if was_locked:
                    unlocked_count += 1
                    print("비밀번호 해제됨")
                
                customers, amounts = parse_billing_info(text_content)
                
                if customers:
                    file_results[base_name] = {'customers': customers, 'amounts': amounts}
                    all_customers.extend(customers)
                    all_amounts.extend(amounts)
            else:
                print(f"추출 실패: {os.path.basename(html_file)}")
        
        # 결과 출력
        print(f"\n{'='*50}")
        print(f"처리 결과")
        print(f"{'='*50}")
        print(f"총 파일: {len(html_files)}개, 성공: {processed_count}개, 비밀번호 해제: {unlocked_count}개")
        
        if all_customers:
            print(f"\n고객명 리스트 (총 {len(all_customers)}개):")
            for i, customer in enumerate(all_customers, 1):
                print(f"{i:2d}. {customer}")
            
            print(f"\n금액 리스트:")
            for i, amount in enumerate(all_amounts, 1):
                print(f"{i:2d}. {amount}")
            
            print(f"\n파일별 결과:")
            for filename, result in file_results.items():
                if result['customers']:
                    print(f"{filename}:")
                    for customer, amount in zip(result['customers'], result['amounts']):
                        print(f"  • {customer} → {amount}")
        
    finally:
        driver.quit()

def main():
    print("최적화된 HTML 고지서 추출기")
    print("=" * 50)
    
    if not os.path.exists(INPUT_FOLDER):
        print(f"'{INPUT_FOLDER}' 폴더가 존재하지 않습니다.")
        return
    
    process_html_files()
    print("\n처리 완료!")

if __name__ == "__main__":
    main()
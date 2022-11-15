from webdriver_manager.chrome import ChromeDriverManager
from seleniumwire import undetected_chromedriver
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import re
import json
from datetime import datetime
from numpy import random
import requests
from os import path, makedirs
import pathlib
import uuid
import argparse

# Search engine based variables
_SEARCH_ENGINE_URL =  'https://duckduckgo.com/'
_SEARCH_ENGINE_BAR_ID = 'search_form_input_homepage'

# Variables referencing the initial cookies banner
_CANCEL_COOKIES_BUTTON_ID = 'W0wltc'

# Variable referencing website's html's structure
_ERROR_PAGE_CLASS_NAME = 'error-page'
_ANSWER_EXPLANATION_CLASS_NAME = 'answer-description'
_CORRECT_ANSWER_CLASS_NAME = 'correct-hidden'
_CORRECT_ANSWER_IMG_PARENT_CLASS_NAME = 'correct-answer'
_ANSWERS_CLASS_NAME = 'multi-choice-item'
_FORMULATION_CLASS_NAME = 'card-text'
_IMAGES_CLASS_NAME = 'in-exam-image'
_IMAGE_NAME_RE = '(.*/)([^/]+)'
_ANSWER_RE = "(\w\.\s+)(.*)"

# Other constants used by functions
_EXCEEDED_MAX_SKIPPED_QUESTIONS_MSG = '[Error] Exceeded amount of admissible skipped questions in a row... Exiting.'
_DEFAULT_ERROR_LOG = './error_log.txt'
_SKIPPED_QUESTION_BASE_MSG = '[Skip] Skipping question #%s'
_EXECUTION_ENDED_BASE_MSG = '[Info] Execution finished with exit code %s'
_IMAGES_DOWNLOAD_DIR = './questions_images'
_QUESTIONS_JSON_FILE = './questions.json'
_DEFAULT_MAX_SKIPPED_QUESTIONS = -1

# Exit codes
_HARD_ERROR_EXIT_CODE = 1
_DENIED_ACCESS_EXIT_CODE = 3
_ALL_OK_EXIT_CODE = 0
_SEVERAL_URLS_NOT_FOUND_EXIT_CODE = 2
_EXCEEDED_MAX_SKIPPED_QUESTIONS_EXIT_CODE = 4


class WebsiteAccessDeniedError(Exception):
    _default_message = '[Error] Access banned to website.'

    def __init__(self, msg=_default_message):
        super().__init__(msg)


class WebsiteUrlNotFoundError(Exception):
    _default_base_message = '[Error] Could not find a valid url to question #%s'

    def __init__(self, question_id=None):
        if question_id is not None:
            super().__init__(WebsiteUrlNotFoundError._default_base_message % question_id)
        else:
            super().__init__()


class WebsiteStructureChangedError(Exception):
    _default_message = '[Error] Any of the websites\' structure has changed, so the script does not work anymore.'

    def __init__(self, msg=_default_message):
        super().__init__(msg)


def get_skip_msg(question_id): return _SKIPPED_QUESTION_BASE_MSG % str(question_id)


def get_random_number(low, high): return random.uniform(low=low, high=high)


def random_wait(low=1, high=5):
    sleep(get_random_number(low=low, high=high))


def write_to_errlog(msg, errlog_path):
    errlog_path = _DEFAULT_ERROR_LOG if errlog_path is None else errlog_path
    with open(errlog_path, mode='a', encoding='utf-8') as f:
        f.write(msg)
        f.write('\n')


def get_driver():
    chrome_options = undetected_chromedriver.ChromeOptions()
    try:
        driver = undetected_chromedriver.Chrome(
            options=chrome_options, seleniumwire_options={})
    except:
        ChromeDriverManager().install()
        driver = undetected_chromedriver.Chrome(
            options=chrome_options, seleniumwire_options={})
    finally:
        return driver


def is_error_page(driver):
    try:
        driver.find_element(By.CLASS_NAME, _ERROR_PAGE_CLASS_NAME)
        return True
    except:
        return False


def close_cookie_banner_if_present(driver):
    try:
        # close cookies banner if present
        close_button = driver.find_element(By.ID, _CANCEL_COOKIES_BUTTON_ID)
        print('[Info] Cookies detected')
        if close_button is not None:
            close_button.click()
    except:
        pass
        #print('[Info] No cookies banner detected')


def remove_answer_prefix(answer):
    matches = re.match(_ANSWER_RE, answer)
    return answer if matches is None else matches.group(2)


def extract_image_name(img_url):
    matches = re.match(_IMAGE_NAME_RE, img_url)
    return None if matches is None else matches.group(2)


def defrag_filename(filename):
    p = pathlib.Path(filename)
    return {'full_name': str(p.absolute()), 'file_name': str(p.name), 'base_name': str(p.stem), 'extension': str(p.suffix), 'parent': str(p.parent)}


def generate_new_base_name(): return uuid.uuid4().hex


def get_uniq_file_path(filename):
    defragmented_filename = defrag_filename(filename)
    new_name = defragmented_filename['full_name']
    while path.exists(new_name):
        new_name = path.join(defragmented_filename['parent'], '%s%s'%(generate_new_base_name(), defragmented_filename['extension']))
    return pathlib.Path(new_name)


def download_images(imgs_urls, download_dir):
    # makes download dir if it does not exist
    makedirs(download_dir,exist_ok=True)
    img_names = []
    for img_url in imgs_urls:
        img_name = extract_image_name(img_url)
        img_full_name = path.join(download_dir, img_name)
        img_path = get_uniq_file_path(img_full_name)
        img_full_name = str(img_path.absolute())
        img_name = str(img_path.name)
        img_names.append(img_name)
        img_request = requests.get(img_url, allow_redirects=True)
        with open(img_full_name, 'wb') as f:
            f.write(img_request.content)
    return img_names


def get_questions_imgs(webelement):
    try:
        found_imgs = webelement.find_elements(By.CLASS_NAME, _IMAGES_CLASS_NAME)
        imgs_urls = [img.get_attribute('src') for img in found_imgs]
        return download_images(imgs_urls=imgs_urls, download_dir=_IMAGES_DOWNLOAD_DIR)
    except:
        return None


def extract_text_from_webelement(webelement):
    t = webelement.get_attribute('innerHTML') if webelement.tag_name == 'span' else webelement.text
    return t.strip().replace('<br>','\n') if t is not None else t


def make_question(driver, id):
    formulation = driver.find_element(By.CLASS_NAME, _FORMULATION_CLASS_NAME)
    formulation_imgs = get_questions_imgs(formulation)
    formulation_text = extract_text_from_webelement(formulation)
    answers = driver.find_elements(By.CLASS_NAME, _ANSWERS_CLASS_NAME)
    answers = [remove_answer_prefix(extract_text_from_webelement(answer)) for answer in answers]
    correct_answer = driver.find_elements(By.CLASS_NAME, _CORRECT_ANSWER_CLASS_NAME)
    correct_answer = [remove_answer_prefix(extract_text_from_webelement(answer)) for answer in correct_answer]
    answer_explanation = driver.find_element(By.CLASS_NAME, _ANSWER_EXPLANATION_CLASS_NAME)
    answer_explanation = extract_text_from_webelement(answer_explanation)
    correct_answer_imgs = None
    try:
        correct_answer_parent = driver.find_element(By.CLASS_NAME, _CORRECT_ANSWER_IMG_PARENT_CLASS_NAME)
        correct_answer_imgs = get_questions_imgs(correct_answer_parent)
    except:
        pass
    
    return {
        'id': id,
        'formulation': formulation_text,
        'formulation_images': formulation_imgs,
        'answers': answers,
        'correct_answer': correct_answer,
        'correct_answer_images': correct_answer_imgs,
        'explanation': answer_explanation
    }


def get_link_element_for_searched_url(driver, search_params, website_url_re, search_engine_url=_SEARCH_ENGINE_URL):
    try:
        # Gets into the search engine website
        driver.get(search_engine_url)
        close_cookie_banner_if_present(driver)
        search_bar = driver.find_element(By.ID, _SEARCH_ENGINE_BAR_ID)
        del driver.requests
        search_bar.send_keys(search_params + Keys.RETURN)
        random_wait()

        # Gets all urls found by search engine
        a_tags = driver.find_elements(By.TAG_NAME, 'a')
        all_urls = [a.get_attribute('href') for a in a_tags]

        # Looks for the website url
        matches_website_url = [url for url in all_urls if re.match(website_url_re, str(url)) is not None]

        if len(matches_website_url):
            website_url = matches_website_url[0]
            a_tag = [a for a in  a_tags if a.get_attribute('href') == website_url]
            return a_tag[0]
        else:
            return None
    except:
        raise WebsiteStructureChangedError()



def get_question_from_search(search_params_base, driver, url_re_base, question_id, search_engine_url=_SEARCH_ENGINE_URL):

    a_tag = get_link_element_for_searched_url(driver=driver, search_params=search_params_base%question_id, website_url_re=url_re_base%question_id, search_engine_url=search_engine_url)
    if a_tag is None:
        raise WebsiteUrlNotFoundError(question_id=question_id)
    a_tag.click()
    random_wait()
    if not is_error_page(driver=driver):
        return make_question(driver=driver, id=question_id)
    else:
        raise WebsiteAccessDeniedError()


def save_to_json(questions, json_path):
    try:
        jsonString = json.dumps(questions, indent=2)
        with open(json_path, mode='w', encoding='utf-8') as f:
            f.write(jsonString)
        return True
    except:
        return False


def load_questions_from_json(json_path):
    with open(json_path, mode='r', encoding='utf-8') as datafile:
        loaded_questions = json.load(datafile)
    return loaded_questions


def print_and_errlog(msg, error_log_path):
    write_to_errlog(msg=msg,errlog_path=error_log_path)
    print(msg)


def sort_questions(questions):
    sort_criteria = lambda q: q['id']
    questions.sort(key=sort_criteria)


if __name__ == '__main__':

    args_parse = argparse.ArgumentParser(description='A custom webscrapper for a certain website...')
    args_parse.add_argument('--first_question', help='the number of the first question that is going to be searched. Default value is 1', type=int, default=1)
    args_parse.add_argument('--last_question', help='the number of the last question that is going to be searched', type=int)
    args_parse.add_argument('--json_file', help='the input/output json file\'s path. Default value is ' + _QUESTIONS_JSON_FILE, type=str, default=_QUESTIONS_JSON_FILE)
    args_parse.add_argument('--search_params_base', help='the search parameters with just one integer format symbol. These are the key words that are going to be searched on the search engine. They are combined with the question number. Example value: "some params question %%d"', type=str)
    args_parse.add_argument('--url_regex_base', help='the regex for the url to navigate on after the search. It must have an integer format symbol. The base name will be combined with the question number. Example value: "https?://www.somewebsite.com/something-being-\w+-and-with-number-%%d"', type=str)
    args_parse.add_argument('--max_skipped', help='the maximum amount of skipped questions on a row before the script stops. If set to a negative number, it assumes that no limit is stablished. Questions are skipped when the url to the website is not found. Default value is ' + str(_DEFAULT_MAX_SKIPPED_QUESTIONS), type=int, default=_DEFAULT_MAX_SKIPPED_QUESTIONS)
    args_parse.add_argument('--error_log_path', help='the location in which the error log will be saved. Default is ' + _DEFAULT_ERROR_LOG, default=_DEFAULT_ERROR_LOG, type=str)
    args_parse.add_argument('--images_download_dir', help="the destination folder to save downloaded images. Default is " + _IMAGES_DOWNLOAD_DIR, default=_IMAGES_DOWNLOAD_DIR, type=str)

    args = args_parse.parse_args()

    skipped_questions_in_a_row = 0   
    first_question = args.first_question
    last_question = args.last_question
    json_file = args.json_file
    error_message = None
    exit_code = _ALL_OK_EXIT_CODE
    search_params_base = args.search_params_base
    url_re_base = args.url_regex_base
    max_skipped_questions = args.max_skipped
    error_log = args.error_log_path
    _IMAGES_DOWNLOAD_DIR = args.images_download_dir

    loaded_questions  = []

    try:
        loaded_questions = load_questions_from_json(json_path=json_file)
        loaded_questions = loaded_questions if loaded_questions is not None else []
        sort_questions(loaded_questions)
    except:
        pass

    questions_numbers_left_to_search = [n for n in range(first_question, last_question + 1, 1) if int(n) not in [int(question['id']) for question in loaded_questions]]

    write_to_errlog('------------- %s --------------\n'%datetime.now(), errlog_path=error_log)
    write_to_errlog(str(questions_numbers_left_to_search) + '\n', error_log)
    print(questions_numbers_left_to_search)

    driver = get_driver()

    all_questions = [] + loaded_questions

    for n in questions_numbers_left_to_search:
        print('[Info] Currently searching for question #%d'%int(n))
        try:
            question = get_question_from_search(search_params_base=search_params_base, driver=driver, url_re_base=url_re_base, question_id=int(n))
            all_questions.append(question)
            save_to_json(questions=all_questions, json_path=json_file)
            skipped_questions_in_a_row = 0
            random_wait()
        except WebsiteAccessDeniedError as ex:
            exit_code = _DENIED_ACCESS_EXIT_CODE
            error_message = str(ex)
            print_and_errlog(error_message, error_log)
            exit(exit_code)
        except WebsiteUrlNotFoundError as ex:
            exit_code = _SEVERAL_URLS_NOT_FOUND_EXIT_CODE
            error_message = str(ex)
            skipped_questions_in_a_row += 1
            print_and_errlog(error_message, error_log)
            if max_skipped_questions >= 0 and skipped_questions_in_a_row >= max_skipped_questions:
                print_and_errlog(_EXCEEDED_MAX_SKIPPED_QUESTIONS_MSG, error_log)
                exit_code = _EXCEEDED_MAX_SKIPPED_QUESTIONS_EXIT_CODE
                exit(exit_code)
        except (WebsiteStructureChangedError, Exception) as ex:
            exit_code = _HARD_ERROR_EXIT_CODE
            error_message = str(ex)
            print_and_errlog(error_message, error_log)
            exit(exit_code)

    print_and_errlog(_EXECUTION_ENDED_BASE_MSG%str(exit_code), error_log)
    exit(exit_code)
    

    
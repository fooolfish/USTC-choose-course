import requests
import json
import re
from time import sleep
from bs4 import BeautifulSoup
from login import login
from random import uniform
from send_mail import send_mail
from config import HEADERS, HEADERS_JSON, MAX_TIME


def code_to_ID(all_lessons, code):
    if code == None:
        result = None
    else:
        result = None
        for item in all_lessons:
            if item['code'] == code:
                result = str(item['id'])
                break

    return result


def get_student_ID(brow):
    course_select = 'https://jw.ustc.edu.cn/for-std/course-select'
    temp = brow.get(course_select, headers=HEADERS, allow_redirects=False)
    return temp.headers['location'].split('/')[-1]


def get_course_select_Turn_ID(brow, student_ID):
    data_for_open_turn = {
        'bizTypeId': '2',
        'studentId': student_ID,
    }
    open_turns = 'https://jw.ustc.edu.cn/ws/for-std/course-select/open-turns'
    temp_1 = brow.post(open_turns, headers=HEADERS,
                       data=data_for_open_turn, allow_redirects=False)
    temp_2 = BeautifulSoup(temp_1.text, 'lxml')
    temp_2 = json.loads(temp_2.p.string)
    return str(temp_2[0]['id'])


def get_addable_lessons_json(brow, course_select_Turn_ID, student_ID):
    get_ID_url = 'https://jw.ustc.edu.cn/ws/for-std/course-select/addable-lessons'
    get_ID_data = {
        'turnId': course_select_Turn_ID,
        'studentId': student_ID
    }
    addable_lessons = brow.post(
        get_ID_url, data=get_ID_data, headers=HEADERS, allow_redirects=False)
    return json.loads(addable_lessons.text)


def get_semester_ID(semester_ID_temp):
    semester_ID = BeautifulSoup(semester_ID_temp.text, 'lxml')
    semester_ID = str(semester_ID)
    pattern = re.compile(r'semesterId:\s\d{1,5},')
    semester_ID = pattern.findall(semester_ID)
    assert len(semester_ID) == 1
    pattern_2 = re.compile(r'\d+')
    return pattern_2.findall(semester_ID[0])[0]


def choose_course(new_course_code, PERIOD, old_course_code=None, reason=None, stable_mode=False):
    brow = login()

    student_ID = get_student_ID(brow)

    course_select_Turn_ID = get_course_select_Turn_ID(brow, student_ID)

    addable_lessons_json = get_addable_lessons_json(
        brow, course_select_Turn_ID, student_ID)

    new_course_ID = code_to_ID(addable_lessons_json, new_course_code)
    old_course_ID = code_to_ID(addable_lessons_json, old_course_code)

    if old_course_ID != None:
        course_select = 'https://jw.ustc.edu.cn/for-std/course-select'
        url_temp = course_select + '/' + student_ID + \
            '/turn/' + course_select_Turn_ID + '/select'
        semester_ID_temp = brow.get(
            url_temp, headers=HEADERS, allow_redirects=False)
        semester_ID = get_semester_ID(semester_ID_temp)

    count = 1
    while True:
        print("正在第 %d 次尝试..." % count)
        count += 1

        if stable_mode:
            print("重新登录中...")
            brow = login()
            # Must add this, or new "brow" can't get/post in following request
            get_student_ID(brow)

        if old_course_ID == None:
            seletion_url = 'https://jw.ustc.edu.cn/ws/for-std/course-select/add-request'
            seletion_data = {
                'studentAssoc': student_ID,
                'lessonAssoc': new_course_ID,
                'courseSelectTurnAssoc': course_select_Turn_ID,
                'scheduleGroupAssoc': '',
                'virtualCost': '0'
            }

            # TODO
            # 此处删掉的内容约 3 行左右，
            # 用于得到直选课时的 request_ID

        else:
            pre_check_url = 'https://jw.ustc.edu.cn/for-std/course-adjustment-apply/preCheck'
            pre_check_data = [{
                'oldLessonAssoc': int(old_course_ID),
                'newLessonAssoc': int(new_course_ID),
                'studentAssoc': int(student_ID),
                'semesterAssoc': int(semester_ID),
                'bizTypeAssoc': 2,
                'applyReason': reason,
                'applyTypeAssoc': 5,
                'scheduleGroupAssoc': None
            }]
            pre_check_data = json.dumps(pre_check_data)

            brow.post(pre_check_url, data=pre_check_data,
                      headers=HEADERS_JSON, allow_redirects=False)

            change_url = 'https://jw.ustc.edu.cn/for-std/course-adjustment-apply/add-drop-request'
            change_data = {
                'studentAssoc': int(student_ID),
                'semesterAssoc': int(semester_ID),
                'bizTypeAssoc': 2,
                'applyTypeAssoc': 5,
                'checkFalseInsertApply': False,
                'lessonAndScheduleGroups': [{
                    'lessonAssoc': int(new_course_ID),
                    'dropLessonAssoc': int(old_course_ID),
                    'scheduleGroupAssoc': None
                }]
            }

            # TODO
            # 此处删掉的内容约 4 行左右，
            # 用于得到换班时的 request_ID

        sleep(PERIOD * 0.5 * uniform(0.6, 1.4))

        add_drop_url = 'https://jw.ustc.edu.cn/ws/for-std/course-select/add-drop-response'
        add_drop_data = {
            'studentId': student_ID,
            'requestId': request_ID
        }

        # print("Request ID " + request_ID)

        temp_5 = brow.post(add_drop_url, data=add_drop_data,
                           headers=HEADERS, allow_redirects=False)
        temp_5 = BeautifulSoup(temp_5.text, 'lxml')
        temp_5 = json.loads(temp_5.p.string)

        if temp_5 == None:
            print("响应为空，重试...")
        elif temp_5['success'] == True:
            print("选课成功，程序退出！")
            send_mail('选课成功，程序退出！', '选课成功，程序退出！')
            break
        else:
            print("选课失败，失败原因： " + temp_5['errorMessage']['textZh'])

        sleep(PERIOD * 0.5 * uniform(0.6, 1.4))


if __name__ == "__main__":
    # 直选：new_course_code, PERIOD
    # 换班：new_course_code, PERIOD, old_course_code, reason
    # add "stable_mode=True" to choose stable mode, or False acquiescently.

    # choose_course('011163.02', 1, '011163.01', '余磊', stable_mode=True)
    # choose_course('011163.02', 1, stable_mode=True)
    # choose_course('001511.02', 1)
    for i in range(MAX_TIME):
        try:
            choose_course('001511.02', 10, stable_mode=True)
            break
        except Exception as e:
            tmp = "第%d次出现异常！" % (i+1)
            print(tmp)
            print(e)
            send_mail(tmp, str(e))
            sleep(30)
            continue

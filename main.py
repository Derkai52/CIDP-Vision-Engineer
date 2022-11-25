
#-----------------------------------------------------------------------------------------#
#     ______    ____    ____     ____          ______                                     #
#    / ____/   /  _/   / __ \   / __ \        /_  __/ ___    ____ _   ____ ___            #
#   / /        / /    / / / /  / /_/ / ______  / /   / _ \  / __ `/  / __ `__ \           #
#  / /___    _/ /    / /_/ /  / ____/ /_____/ / /   /  __/ / /_/ /  / / / / / /           #
#  \____/   /___/   /_____/  /_/             /_/    \___/  \__,_/  /_/ /_/ /_/            #
#                                                                                         #
#          ____            __              __  ___                  __                    #
#         / __ \  ____    / /_   ____     /  |/  / ____ _   _____  / /_  ___    _____     #
#        / /_/ / / __ \  / __ \ / __ \   / /|_/ / / __ `/  / ___/ / __/ / _ \  / ___/     #
#       / _, _/ / /_/ / / /_/ // /_/ /  / /  / / / /_/ /  (__  ) / /_  /  __/ / /         #
#      /_/ |_|  \____/ /_.___/ \____/  /_/  /_/  \__,_/  /____/  \__/  \___/ /_/          #
#                                                                                         #
#---------------------<< Designed by SX-CV-RobotTeam in 2022 >>---------------------------#

# 本程序使用 1280 * 720 作为输入图像尺寸

import cv2 as cv
import numpy as np

from communite import MessageProcesser
from auto_alignment.move import Move
from block_correction.correction import Cube, Tools


if __name__ == "__main__": # TODO: 这里写的很乱，两套代码建议重新解耦通信模块，整合一下代码范式。
    # messageProcesser = MessageProcesser(is_vofa=False)
    # 工程执行模式选择 1、兑换站自动对位  2、矿石自动翻转
    task_model = int(input("请输入需要启用的模式:\n  1、兑换站自动对位  2、矿石自动翻转\n"))
    if task_model == 1:
        move=Move()
        while True:
            print("***********开始执行兑换站自动对位***************")
            move.move_to_station()

    elif task_model == 2:
        # cap = cv.VideoCapture("../test/hik_test.avi")
        cap = cv.VideoCapture(0)
        cube = Cube()
        test_tools = Tools()
        while cap.isOpened():
            ret, image = cap.read()
            if not ret:
                break
            if cv.waitKey(1) == (ord('d') or ord('D')):  # 对图像按下d键即可进入debug图像模式
                test_tools.debugHsv(image)
            # image = cv.resize(image, (640, 480))
            cube.main(image)  # 程序主入口

    else:
        print("模式选择有误！")





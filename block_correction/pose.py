import cv2
import numpy as np
import math


def solve_pnp(object_2d):
    """
        建立以矿石面中心为原点的世界坐标系，特征对应的点位顺序为:
            1——————2
            |      |
            |      |
            4——————3
    """
    object_3d_points = np.array(([-80, -80, 0],
                                 [80, -80, 0],
                                 [80, 80, 0],
                                 [-80, 80, 0]), dtype=np.double)


    # 这里是传入的二维坐标，也就是鼠标垫四个角点在图中的像素点位置
    object_2d_point = np.array(object_2d, dtype=np.double)
    camera_matrix = np.array(([598.29493, 0, 304.76898],
                             [0, 597.56086, 233.34762],
                             [0, 0, 1.0]), dtype=np.double)
    dist_coefs = np.array([-0.53572,1.35993,-0.00244,0.00620,0.00000], dtype=np.double)
    # 求解相机位姿
    found, rvec, tvec = cv2.solvePnP(object_3d_points, object_2d_point, camera_matrix, dist_coefs)
    rotM = cv2.Rodrigues(rvec)[0]
    camera_postion = -np.matrix(rotM).T * np.matrix(tvec)

    theta_x = math.atan2(rotM[2][1], rotM[2][2])* (180 / math.pi)
    theta_y = math.atan2(-rotM[2][0],math.sqrt(rotM[2][1]*rotM[2][1] + rotM[2][2])*rotM[2][2])* (180 / math.pi)
    theta_z = math.atan2(rotM[1][0], rotM[0][0])* (180 / math.pi)


    # print(theta_x, theta_y, theta_z)
    # print("camera pose:", camera_postion.T)
    return camera_postion.T, [theta_x, theta_y, theta_z]


def _order_points(pts):
    """ 点位排序
    排序后的点位顺序为:
            1——————2
            |      |
            |      |
            4——————3
    """
    rect = np.zeros((4, 2), dtype="float32")

    # 计算点坐标XY之和
    # 左上角点的和最小，而右下角的点总和最大
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # 计算点坐标XY之间的差值
    # 右上角的差异最小，而左下角的差异最大
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect


def four_point_transform(points, tmpWidth, tmpHeight, image):
    """ 四点透视变换 """
    # 获取一致的特征点顺序，并将其拆包
    pts = np.array(points)
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect

    dst = np.array([
        [0, 0],
        [tmpWidth - 1, 0],
        [tmpWidth - 1, tmpHeight - 1],
        [0, tmpHeight - 1]], dtype="float32")

    # 生成透视变换矩阵图像
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (tmpWidth, tmpHeight))
    cv2.imshow("PerspectiveTrans", warped)

    return warped
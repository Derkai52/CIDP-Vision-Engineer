import cv2 as cv
from utils.config_generator import configObject


def classic(img):
    """ 模板匹配 """
    target_R_top = cv.imread("template/label_R_top.jpg")
    target_R_left = cv.imread("template/label_R_left.jpg")
    target_R_right = cv.imread("template/label_R_right.jpg")
    target_R_bottom = cv.imread("template/label_R_bottom.jpg")
    target_Top = cv.imread("template/label_top.jpg")
    target_Barcode = cv.imread("template/label_barCode.jpg")
    templates = [target_Top, target_Barcode,
                 target_R_top, target_R_left,
                 target_R_right, target_R_bottom] # 由于检测的原因，让不容易检测的先放到前面检测

    th, tw = img.shape[:2]
    cv.imshow("fsefsfsefe", img)

    for i, tmp in enumerate(templates):
        result = cv.matchTemplate(tmp, img, cv.TM_CCOEFF_NORMED) # [cv.TM_SQDIFF_NORMED, cv.TM_CCORR_NORMED, cv.TM_CCOEFF_NORMED]
        # print("result:", result)  # 置信度

        # 匹配置信度筛选
        if result >= configObject.detection_config.tmpThreshold:
            cv.imshow("target", tmp)
            print(i)
            return i+1

    return False

    ## 获得最佳匹配的区域
    # min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)
    # if cv.TM_CCOEFF_NORMED == cv.TM_SQDIFF_NORMED:
    #     tl = min_loc
    # else:
    #     tl = max_loc
    # br = (tl[0] + tw, tl[1] + th)

    # cv.rectangle(image, tl, br, (0, 255, 0), 2)
    # cv.imshow("match-" + str(md), image)
    # cv.putText(img, max_val, (10, 30), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv.LINE_AA, 0)
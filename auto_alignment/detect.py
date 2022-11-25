import math
import cv2 as cv
import numpy as np
from auto_alignment import tools
from camera import RS, SHOW_IMAGE_FLAG, DEBUG_FLAG, get_camera_data


class DetectStation:
    def __init__(self):
        #相机参数
        self.color_image=None
        self.depth_image=None
        self.color_map=None
        self.camera=RS(open_depth=True,open_color=True,frame=15)

        #识别参数
        self.error=50#允许最大误差
        self.target_legnth=400#目标尺寸

        #上一帧识别结果
        self.last_point=None

    def get_pointrect_mask(self,point=None,rect_w=50,rect_h=30,show_image=False):
        """
        送入深度图,基于point的点生成矩形,对矩形的所处平面进行mask的分割
        :param point: 矩形中心点,如果不指定则为全图中心
        :param rect_w: 矩形w
        :param rect_h: 矩形h
        :param show_image:展示图片
        :return: 识别的mask
        """
        #1:获取xyz矩阵
        xyz_image=self.camera.get_xyz_image()

        #2:生成搜索的ROI
        point_x,point_y=point
        roi=xyz_image[point_y-rect_h:point_y+rect_h,point_x-rect_w:point_x+rect_w]
        roi=roi.reshape(-1,3)#用于统一尺寸

        #3:开始基于mask找到目标
        #计算深度值,滤除超过2*方差的点
        mean=np.mean(roi[:,2])
        std=np.std(roi[:,2])
        correct_index=abs(roi[:,2]-mean)<2*std#进行一次滤波,避免最小二乘法效果不好
        filtered_roi=roi[correct_index]#索引误差不超过2*std的

        #4:求取平面矩阵
        if np.linalg.det(filtered_roi.T@filtered_roi)==0:
            return np.zeros(xyz_image.shape,dtype=np.uint8)#如果矩阵出现逆解则直接返回全黑的Mask

        Y=-np.ones(filtered_roi.shape[0])
        plane_param=np.linalg.inv(filtered_roi.T@filtered_roi)@filtered_roi.T@Y#生成平面参数
        all=math.sqrt(plane_param[0]*plane_param[0]+plane_param[1]*plane_param[1]+plane_param[2]*plane_param[2])#计算平面的x^2+y^2+z^2

        distance_array=abs(xyz_image.dot(plane_param)+1)/all#获取与生成平面距离的值
        mask=cv.inRange(distance_array,0,self.error)#mask允许的误差

        #5:进行形态学操作
        processed_mask=cv.morphologyEx(mask,cv.MORPH_CLOSE,tools.generate_kernel(20,20))#形态学操作提升结果
        processed_mask=cv.morphologyEx(processed_mask,cv.MORPH_OPEN,tools.generate_kernel(100,30))

        if show_image:
            self.color_map=self.camera.get_color_map()
            self.color_map[point_y-rect_h:point_y+rect_h,point_x-rect_w,point_x+rect_w]=(0,0,255)
            if SHOW_IMAGE_FLAG:
                cv.imshow("{},{}mask".format(point_x,point_y),self.color_map)

        return processed_mask

    def check_x_correct(self,middle_xyzs):
        """
        送入中心矩形框的xyz值,查看是否为目标
        :param middle_xyzs:中心矩形的xyzs
        :return:
        """
        distance1=tools.get_distance(middle_xyzs[0],middle_xyzs[3])
        distance2=tools.get_distance(middle_xyzs[1],middle_xyzs[2])

        X_temp=(distance1+distance2)/2
        X_correct=abs(X_temp-self.target_legnth/2)<self.error

        if DEBUG_FLAG:
            print("正确的X_temp为:",X_temp,"期望的距离为:",self.target_legnth/2)
            print("检测到的rect的X_temp为:",X_temp,"期望的距离为:",self.target_legnth/2)

        return X_correct

    def check_rect(self,point,rect):
        """
        基于找到的矩形进行多重确定,确保是目标值
        :param point:寻找的中心点
        :param rect: 矩形
        :return:
        """
        #1:确保矩形是包含点的
        in_rect_flag=tools.is_in_rect(point,rect)
        if not in_rect_flag:
            return None,[],[]

        #2:确定矩形的xyz符合要求
        fourpoints=cv.boxPoints(rect)
        correct_points=tools.sort_four_points(fourpoints,rect[0])

        middle_points=[]
        middle_xyzs=[]
        for point in correct_points:#获取每个点的值
            if point is None:#为什么要加这个限制?这个不懂
                if DEBUG_FLAG:
                    print("有时候会进入到这个的状态,这里面的输出为:",correct_points)
                return False,middle_points,middle_xyzs
            middle_points.append(tools.get_middle(rect[0],point))
            middle_xyzs.append(self.camera.get_xyz(middle_points[-1]))


        #2.2:确保x方向符合要求
        return self.check_x_correct(middle_xyzs),middle_points,middle_xyzs

    def get_best_rect(self,rects_list,rects_xyz_list,rects_center):
        """
        对于找到的一堆矩形选取最为正确的
        :param rects_list: 矩形4个点的list
        :param rects_xyz_list: 矩形xyz的4个点
        :return:
        """
        if len(rects_list)==1:
            return rects_list[0],rects_xyz_list[0],rects_center[0]

        elif len(rects_list)==0:
            return None,None,None

        else:#多于1个的情况
            if DEBUG_FLAG:
                print("出现了多个矩形的情况,他们的矩形情况为:")
                print(rects_list)
                print(rects_xyz_list)
            correct=self.error
            correct_i=0
            for i,middle_xyzs in enumerate(rects_xyz_list):
                distance1=tools.get_distance(middle_xyzs[0],middle_xyzs[3])
                distance2=tools.get_distance(middle_xyzs[1],middle_xyzs[2])

                temp=abs((distance1+distance2)/2-self.target_legnth/2)-self.error
                if temp<correct:
                    correct_i=i

            return rects_list[correct_i],rects_xyz_list[correct_i],rects_center[correct_i]

    def get_target_frommask(self,mask,center_point):
        """
        :param mask:找到的mask寻找矩形框
        :param center_point: 基于中心点寻找的mask
        送入mask,找到对应的尺寸
        :return:
        """
        rects_list=[]
        rects_xyz_list=[]
        rects_center=[]
        try:
            contours,hierarchy=cv.findContours(mask,cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE)
        except:
            return False,None,None


        for contour in contours:
            #2.1:筛选掉小的矩形
            if cv.contourArea(contour)<30000:
                continue#区域太小直接跳过

            #2.2:确保找到的mask都在矩形中
            rect=cv.minAreaRect(contour)
            find_station_flag,middle_points,middle_xyzs=self.check_rect(center_point,rect)
            if find_station_flag:
                rects_list.append(middle_points)
                rects_xyz_list.append(middle_xyzs)
                rects_center.append((int(rect[0][0]),int(rect[0][1])))

        target_rect,target_rect_xyz,target_center=self.get_best_rect(rects_list,rects_xyz_list,rects_center)
        if target_rect is not None:
            #找到了资源岛,更新last_point
            self.last_point=target_center
            return True,target_rect,target_rect_xyz
        else:
            return False,None,None

    def get_station(self,depth_image):
        """
        送入深度图,目标获得资源岛的xyz三个值
        如果没有找到资源岛,则后两个返回值为None
        :param depth_image:
        :return:Find_Flag(是否找到资源岛),target_rect(目标矩形),target_rect_xyz(目标矩形的xyz)
        """
        #1:首先现在上一帧的地方找资源岛,找到则返回True,target_rect,target_rect_xyz
        if self.last_point is not None:
            last_point=self.last_point
            last_mask=self.get_pointrect_mask(last_point)
            find_flag,target_rect,target_rect_xyz=self.get_target_frommask(last_mask,last_point)
            if find_flag:
                return find_flag,target_rect,target_rect_xyz#找到就返回目标

        #2:若上一帧没找到点,则从中心区域开始找,找到就直接返回值
        h,w=depth_image.shape
        center_point=(int(w/2),int(h/2)+60)
        center_mask=self.get_pointrect_mask(center_point)
        find_flag,target_rect,target_rect_xyz=self.get_target_frommask(center_mask,center_point)
        if find_flag:
            return find_flag,target_rect,target_rect_xyz#找到就返回目标

        #5:中心区域仍未找到,则采用一个For循环进行寻找,不断更新中心点
        for i in range(10):
            all_point=(int(w/2+60*(i-5)),int(h/2)+60)
            right_mask=self.get_pointrect_mask(all_point)
            find_flag,target_rect,target_rect_xyz=self.get_target_frommask(right_mask,all_point)
            if find_flag:
                return find_flag,target_rect,target_rect_xyz#找到就返回目标


        #5:如果都没有找到,则返回False
        return False,None,None



def detect_station():
    """
    用于寻找资源岛样例代码
    @return:
    """
    detectStation= DetectStation()#识别类
    while True:
        #1:获取颜色图,深度图,和深度图对应的color_map
        color_image,depth_image=detectStation.camera.get_data()
        color_map=detectStation.camera.get_color_map()

        #2:寻找资源岛
        find_station_flag,station_rect,station_xyz=detectStation.get_station(depth_image)
        if find_station_flag:
            for i in range(4):
                cv.line(color_map,tuple(station_rect[i]),tuple(station_rect[(i+1)%4]),(255,255,255),2)

        #3:进行结果展示
        show_image=cv.hconcat([color_image,color_map])
        cv.namedWindow("result",cv.WINDOW_NORMAL)
        cv.imshow("result",show_image)
        cv.waitKey(1)


if __name__ == '__main__':
    # get_camera_data()#用于测试相机是否能正常开启
    detect_station()#用于测试是否能够检测出资源岛
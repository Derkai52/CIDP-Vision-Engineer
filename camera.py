"""
这里面主要用于进行矩形框的检测任务
"""

import cv2 as cv
import numpy as np
from tqdm import tqdm
import pyrealsense2 as rs


#用于进行不同的debug模式

global DEBUG_FLAG
global SHOW_IMAGE_FLAG
global USE_SERIAL_FLAG

DEBUG_FLAG=False
SHOW_IMAGE_FLAG=True
USE_SERIAL_FLAG=False

class RS:
    def __init__(self,open_depth=True,open_color=True,frame=15,resolution='640x480'):
        """
        初始化相机
        :param open_depth: 是否开启深度
        :param open_color: 是否开启颜色
        :param frame: 帧率设置
        :param resolution: 像素值大小
        """
        #1:确定相机内参(从rs-sensor-control中获取),同时导入矩阵用于进行检测计算xyz图
        all_matrix=np.load("./all_matrix.npz")#.npz文件在类中的generate_xy_matrix()的函数中生成
        if resolution=='640x480':
            self.image_width=640
            self.image_height=480
            self.fx=383.436
            self.fy=383.436
            self.cx=318.613
            self.cy=238.601
            self.x_matrix=all_matrix['x_matrix640']
            self.y_maxtrix=all_matrix['y_matrix640']
            print("640X480")

        elif resolution=='1280x720':
            self.image_width=1280
            self.image_height=720
            self.fx=639.059
            self.fy=639.059
            self.cx=637.688
            self.cy=357.688
            self.x_matrix=all_matrix['x_matrix1280']
            self.y_maxtrix=all_matrix['y_matrix1280']
            print(self.y_maxtrix)
            print("1280x720")

        elif resolution=='848x480':
            self.image_width=848
            self.image_height=480
            self.fx=423.377
            self.fy=423.377
            self.cx=422.468
            self.cy=238.455
            self.x_matrix=all_matrix['x_matrix848']
            self.y_maxtrix=all_matrix['y_matrix848']
            print("848x480")
        else:
            assert False,"请输入正确的resolution值"

        #2:初始化一系列参数
        self.open_depth=open_depth
        self.open_color=open_color
        self.pipeline = rs.pipeline()#开启通信接口
        config_rs = rs.config()

        #2.1:使能深度和颜色图
        if open_depth:
            config_rs.enable_stream(rs.stream.depth, self.image_width, self.image_height, rs.format.z16, frame)
            self.depth_image=None
            self.color_map=None

        if open_color:
            config_rs.enable_stream(rs.stream.color,self.image_width, self.image_height, rs.format.bgr8, frame)
            self.color_image=None

        #2.2:开始通信流
        print(config_rs)


        self.profile=self.pipeline.start(config_rs)

        #2.3:当RGB和深度同时开启时,将颜色图向深度图对齐
        if open_depth and open_color:
            align_to=rs.stream.depth
            self.align=rs.align(align_to)
        else:
            self.align=None


        #3:定义滤波器
        self.dec_filter=rs.decimation_filter(4)#降采样
        # self.temp_filter=rs.temporal_filter(3)#上下帧之间利用时间信息避免跳动,参数看官方文档
        self.hole_filter=rs.hole_filling_filter(2)#hole填充

    def get_data(self):
        """
        用于获取color_image和depth_image
        如果设定中没有就返回None
        :return:
        """
        #对齐帧并获取颜色和深度图帧
        frames=self.pipeline.wait_for_frames()
        if self.align is not None:
            frames=self.align.process(frames)#与深度图对齐

        #获取深度图
        if self.open_depth:
            depth_frame=frames.get_depth_frame()
            #使用滤波器处理
            hole_filtered=self.hole_filter.process(depth_frame)
            dec_filtered=self.dec_filter.process(hole_filtered)
            depth_image=np.asanyarray(dec_filtered.get_data())
            depth_image=cv.resize(depth_image,(self.image_width,self.image_height))

        else:
            depth_image=None



        #获取颜色图
        if self.open_color:
            color_frame=frames.get_color_frame()
            color_image=np.asanyarray(color_frame.get_data())
        else:
            color_image=None


        #生成为类中的图
        self.depth_image=depth_image
        self.color_image=color_image

        return color_image,depth_image

    def get_color_map(self,depth_image=None,range=None):
        """
        送入深度图,返回对应的颜色图
        :param depth_image:需要生成的颜色图,如果为None,则选取自带的深度图
        :param range: 是否需要滤除掉一定距离之后的值
        :return:
        """
        #没有深度图则直接采用类中原本的深度图
        if depth_image is None:
            depth_image=self.depth_image

        #有range要求则进行阈值操作
        range_image=depth_image.copy()
        if range is not None:
            depth_mask=cv.inRange(depth_image,0,range)
            if SHOW_IMAGE_FLAG:
                cv.imshow("depth_mask",depth_mask)
            range_image=depth_image*depth_mask/255

        #开始转深度图
        color_map=range_image.copy()
        cv.normalize(color_map,color_map,255,0,cv.NORM_MINMAX)
        color_map=color_map.astype(np.uint8)
        color_map=cv.applyColorMap(color_map,cv.COLORMAP_JET)
        self.color_map=color_map

        return color_map

    def get_xyz_image(self):
        """
        基于深度图,获取一张xyz_image的图,3通道,分别存放了该像素点的xyz值
        :return:xyz_image
        """
        xyz_image=np.array([self.x_matrix*self.depth_image,self.y_maxtrix*self.depth_image,self.depth_image])
        xyz_image=xyz_image.transpose((1,2,0))
        return xyz_image

    def get_xyz(self,point,range_area=2):
        """
        获取point点的xyz值
        当索引到边上时,会直接所以该点的Z值
        :param point:需要获取xyz的像素点
        :param range_area:取周围邻域的中间值
        :return:np.array((X,Y,Z))
        """
        u,v=point
        u=int(u)
        v=int(v)
        center_Z=[]
        #1:对center_Z进行排序,得到中值作为深度
        try:
            for x in range(-range_area,range_area+1):
                for y in range(-range_area,range_area+1):
                    center_Z.append(self.depth_image[v-y,u-x])#采用行列索引
            center_Z.sort()
            Z=center_Z[int(len(center_Z)/2)]
        except:
            try:
                Z=self.depth_image[v,u]
            except:
                Z=0

        #2:使用外参进行反解
        X=(u-self.cx)*Z/self.fx
        Y=(v-self.cy)*Z/self.fy
        return np.array((X,Y,Z))

    ##############################功能性函数####################################
    def generate_xy_matrix(self):
        """
        用于生成xyz_image的矩阵
        测距点本质上只与z有关,向平面的xy是固定的,由z进行比例放大缩小
        会在这个的目录下生成all_matrix.npz文件,其中包含了对应需要的xy比例的矩阵

        #使用方法:
        # data=np.load("all_matrix.npz")
        # x_640=data['x_matrix640']
        # x_1280=data['x_matrix1280']
        # print(x_640.shape)
        # print(x_1280.shape)
        :return:
        """

        #1:生成1280的矩阵
        x_1280_matrix=np.zeros((720,1280))
        y_1280_matrix=np.zeros((720,1280))
        fx=639.059
        fy=639.059
        cx=637.688
        cy=357.688
        for i in tqdm(range(1280)):
            for j in range(720):
                # print(temp_1280[j,i])#默认的索引是行列索引
                x_1280_matrix[j,i]=(i-cx)/fx
                y_1280_matrix[j,i]=(j-cy)/fy



        #2:生成640的矩阵
        x_640_matrix=np.zeros((480,640))
        y_640_matrix=np.zeros((480,640))
        fx=383.436
        fy=383.436
        cx=318.613
        cy=238.601
        for i in tqdm(range(640)):
            for j in range(480):
                x_640_matrix[j,i]=(i-cx)/fx
                y_640_matrix[j,i]=(j-cy)/fy



        #3:生成848x480的内参
        x_848_matrix=np.zeros((480,848))
        y_848_matrix=np.zeros((480,848))
        fx=423.377
        fy=423.377
        cx=422.468
        cy=238.455

        for i in tqdm(range(848)):
            for j in range(480):
                x_848_matrix[j,i]=(i-cx)/fx
                y_848_matrix[j,i]=(j-cy)/fy

        #保存对应的矩阵
        np.savez('all_matrix.npz', x_matrix640=x_640_matrix, y_matrix640=y_640_matrix, x_matrix1280=x_1280_matrix, y_matrix1280=y_1280_matrix, x_matrix848=x_848_matrix, y_matrix848=y_848_matrix)

    def check_distance(self,roi_size=15):
        """
        用于进行相机深度值确定
        @param roi_size: 定义roi的长宽,从而知道多少范围的roi合适
        @return:
        """
        while True:
            color_image,depth_image=self.get_data()

            #查看测距是否准确,随机取几个点,然后进行测距,看看效果
            color_map=self.get_color_map(depth_image,10000)

            #获取图像中心点
            h,w=depth_image.shape
            h=int(h/2)
            w=int(w/2)

            #生成一个区域进行测距
            xyz_image=self.get_xyz_image()
            roi_w=roi_size
            roi_h=roi_size
            middle_roi=xyz_image[h-roi_h:h+roi_h,w-roi_w:w+roi_w]#得到中心区域的xyz值
            middle_roi=middle_roi.reshape(-1,3)

            #对选取区域求平均之后去除掉方差以外的值
            mean=np.mean(middle_roi[:,2])
            std=np.std(middle_roi[:,2])
            origin_number=len(middle_roi)
            correct_middle_roi=abs(middle_roi[:,2]-mean)<0.8*std#在其内部的roi值
            middle_roi=middle_roi[correct_middle_roi]
            new_number=len(middle_roi)
            print("选取剩余0.8个方差之后的值有:{},剩余值占原来的{:.2f}%".format(new_number,new_number/origin_number*100))

            #得到最终的测试距离
            mean_distance=np.mean(middle_roi[:,2])#获取正确的xyz值

            #最后输出测距距离
            print("中心的距离为:",mean_distance)
            color_map[h-roi_h:h+roi_h,w-roi_w:w+roi_w]=(0,0,255)

            cv.imshow("depth_image",depth_image)
            cv.imshow("color_map",color_map)
            cv.waitKey(0)


##############################样例代码####################################
def get_camera_data():
    """
    用于显示相机图像
    @return:
    """
    camera=RS()
    while True:
        color_image,depth_image=camera.get_data()
        color_map=camera.get_color_map()
        cv.imshow("color_image",color_image)
        cv.imshow("color_map",color_map)
        cv.waitKey(1)


if __name__ == '__main__':
    get_camera_data()#用于测试相机是否能正常开启


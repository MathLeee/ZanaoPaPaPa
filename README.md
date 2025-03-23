# ZanaoPaPaPa
一个赞噢校园集市的爬虫项目
起因是最近大数据的老师莫名其妙布置了一道爬虫当作实验作业，主播我完全从零学起，做完作业后感觉翅膀硬了，就突发奇想做了这个项目

#程序UI：
![image](https://github.com/user-attachments/assets/23d8d955-8008-4fed-8da5-86740c95bd35)
功能可以说很完备了，或许可以做社会调查的时候用到，或许吧（（（

#后人乘凉（鸣谢！！！）：
本项目对于请求头的处理部分参考了zidou-kiyn紫豆大佬的逆向技术，原项目地址如下：
https://github.com/zidou-kiyn/ZanaoRobot

#需要你更改的部分
学校ID（共三处））:
/zanaoget.py如图:
![image](https://github.com/user-attachments/assets/ff416b70-57c7-4b24-a8e5-15659b6c5cae)
/heard_get.js如图：
![image](https://github.com/user-attachments/assets/4a299456-aa4a-4155-a89b-048b8a4be34d)
用户Token（共两处）：
/zanaoget.py如图:
![image](https://github.com/user-attachments/assets/7585d0c9-6ba1-4c4f-ab22-f290fd367b67)
/heard_get.js如图：
![image](https://github.com/user-attachments/assets/4526c88d-794f-4577-99e0-26fe22af2625)
关于用户Token的获取我用的工具是Charles，通过Charles抓取请求头，可自行搜索获取方式，实在不会的话可以留言
关于学校ID，我发现赞噢后端对于默写学校可能用的不是官方缩写，不过这个也在请求头里可以看到







# flask模块用于实现简单的web服务项目
from flask import Flask, render_template, request, flash
# 导入COS相关模块，用于将二维码存入腾讯云对象存储COS
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import sys
# MyQR模块用于实现二维码的制作功能
from MyQR import myqr
# time模块用于生成文件中的时间戳
import time
# 导入配置文件
from config import *

app = Flask(__name__)

# 定义一个secret_key，内容可以随意指定，用于混入消息中进行加密
app.secret_key = "secret_key"

# ---实现主页展示功能---
@app.route('/')
def index():
    # 展示渲染后的主页模板文件
    return render_template('index.html')
# ---实现主页展示功能---

# ---实现二维码导出功能---
@app.route("/export", methods=["POST"])
def export():
    """上传文件函数，用于执行文件上传功能"""
    # 判断请求类型，只对POST请求的操作进行响应
    if request.method == "POST":
        # 获取表单中的 url_str 对应的内容
        url_str = request.form.get('url_str')
        # 如果 url_str 为空，默认使用腾讯云首页
        if not url_str:
            url_str = "https://cloud.tencent.com/"
        # 获取提交的文件对象，此文件通过模板中的表单提交
        upload_file = request.files.get('file')
        # 创建用于区分文件的13位时间戳，此时间戳会拼接在每个文件名的尾部
        time_str = str(int(round(time.time() * 1000)))

        # 如果没有获取到上传文件
        if not upload_file:
            # 拼接导出路径，文件名添加时间戳避免读取缓存
            export_name = "qrcode_{}.png".format(time_str)
            export_path = "./static/export/{}".format(export_name)
            # 生成不含图片的普通二维码
            try:
                myqr.run(url_str, save_name=export_path)
            # 如果生成过程中报错，展示错误信息，并返回主页
            except Exception as e:
                flash("Error: {}".format(e))
                return index()
            # 定义展示图片的标识 show_photo 为True，模板页面将会展示二维码
            show_photo = True

        # 如果上传了图片，保存图片并生成图片二维码
        else:
            # 获取文件名和文件后缀，用于进行判断和文件名生成
            file_name = upload_file.filename
            # 获取文件名的头部，作为生成的文件名头部
            file_header = file_name.split(".")[0]
            # 获取文件的格式尾缀，用于对文件格式进行判断
            file_type = file_name[-4:]
            print(file_type)
            # 如果文件后缀不符，展示提示信息，并跳转到主页
            if file_type not in [".bmp", ".jpg", ".png", ".gif"]:
                # flash可以在模板文件中闪现推送提示信息
                flash("文件格式有误，支持的文件格式为：bmp, jpg, png, gif")
                # 不进行转换操作，直接返回主页
                return index()

            # 定义上传图片的原始路径，用于存储上传的原始路径图片
            save_path = "./static/origin/{}".format(upload_file.filename)
            # 保存上传的原始图片
            upload_file.save(save_path)
            # 拼接导出文件的文件名头部，尾缀将在稍后进行判断
            export_header = "{}_{}".format(file_header, time_str)
            # 拼接导出路径，文件名添加时间戳避免读取缓存
            if file_type in [".bmp", ".jpg", ".png"]:
                export_name = export_header + ".png"
                export_path = "./static/export/{}".format(export_name)
            elif file_type == ".gif":
                export_name = export_header + ".gif"
                export_path = "./static/export/{}".format(export_name)
            # 生成包含图片的二维码（此处定义为生成彩色二维码）
            try:
                myqr.run(url_str,
                picture=save_path,
                colorized=True,
                save_name=export_path)
            # 如果生成过程中报错，展示错误信息，并返回主页
            except Exception as e:
                flash("Error: {}".format(e))
                return index()
            # 定义展示图片的标识 show_photo 为True，模板页面将会展示二维码
            show_photo = True

        # 完成上传后，重新渲染模板页面
        return render_template('index.html', export_path=export_path, show_photo=show_photo, export_name=export_name)
# ---实现二维码导出功能---

# ---实现二维码图片的下载功能---
@app.route("/download/<file_name>")
def download(file_name):
    download_type = request.args.get("type")
    if download_type == "local":
        from flask import Response  # 导入Response模块
        with open("./static/export/{}".format(file_name), "rb") as f:
            fp = f.read()
            response = Response(fp, content_type='application/octet-stream')
            # file_name需要进行编码转换，否则中文文件无法正常下载
            response.headers["Content-disposition"] = 'attachment; filename={}'.format(file_name.encode("utf-8").decode("latin-1"))
            return response
    elif download_type == "cos":
        global secret_id, secret_key, region
        # 执行功能——上传图片到COS存储桶
        secret_id = secret_id
        secret_key = secret_key
        region = region
        config = CosConfig(Region=region, SecretId=secret_id,
                        SecretKey=secret_key)
        client = CosS3Client(config)
        with open("./static/export/{}".format(file_name), "rb") as fp:
            try:
                response = client.put_object(
                    Bucket=bucket_name,
                    Body=fp,
                    Key=file_name,
                    StorageClass='STANDARD',
                    EnableMD5=False
                )
            except Exception as e:
                # 上传文件失败时触发
                flash("Error: {}".format(e))
            else:
                flash("添加成功！COS图片链接为： https://{}.cos.{}.myqcloud.com/{}".format(bucket_name, region, file_name))
        export_path = "/static/export/{}".format(file_name)
        export_name = file_name
        show_photo = True
        return render_template('index.html', export_path=export_path, show_photo=show_photo, export_name=export_name)
# ---实现二维码图片的下载功能---

if __name__ == "__main__":
    # 定义监听host为0.0.0.0，表示此服务可以被外部网络访问
    # 默认监听端口为5000
    app.run(host="0.0.0.0")

# coding: utf-8
import datetime
import json

import requests
from sentry.plugins.bases.notify import NotificationPlugin

import sentry_feishu
from .forms import FeiShuOptionsForm


class FeiShuPlugin(NotificationPlugin):
    """
    Sentry plugin to send error counts to FeiShu.
    """
    author = 'yjy'
    author_url = 'https://github.com/DC-ET/sentry-feishu'
    version = sentry_feishu.VERSION
    description = 'Send error counts to FeiShu.'
    resource_links = [
        ('Source', 'https://github.com/DC-ET/sentry-feishu'),
        ('Bug Tracker', 'https://github.com/DC-ET/sentry-feishu/issues'),
        ('README', 'https://github.com/DC-ET/sentry-feishu/blob/master/README.md'),
    ]

    slug = 'FeiShu'
    title = 'FeiShu'
    conf_key = slug
    conf_title = title
    project_conf_form = FeiShuOptionsForm

    def is_configured(self, project):
        """
        Check if plugin is configured.
        """
        return bool(self.get_option('url', project))

    def notify_users(self, group, event, *args, **kwargs):
        if not self.is_configured(group.project):
            return None
        if self.should_notify(group, event):
            self.post_process(group, event, *args, **kwargs)
        else:
            return None

    def findrepeatstart(self, origin, matchlen):
        if matchlen < 2 or len(origin) <= matchlen:
            return -1
        i = origin.find(origin[0:matchlen], 1)
        if i == -1:
            return self.findrepeatstart(origin, matchlen // 2)
        return i

    def findrepeatend(self, origin):
        return origin.rfind("...")

    def cutrepeat(self, origin):
        repeatstart = self.findrepeatstart(origin, 120)
        if repeatstart == -1:
            return origin
        repeatend = self.findrepeatend(origin)
        if (repeatend == -1):
            return origin
        return origin[0:repeatstart] + origin[repeatend:]

    def post_process(self, group, event, *args, **kwargs):
        """
        Process error.
        """
        if not self.is_configured(group.project):
            return

        if group.is_ignored():
            return

        send_url = self.get_option('url', group.project)
        message = self.cutrepeat(event.message)

        data = {
            "msg_type": "interactive",
            "content": {
                "config": {
                    "wide_screen_mode": True
                },
                "elements": [
                    {
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "content": u"**🗳 系统名称**\n " + event.project.slug,
                                    "tag": "lark_md"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "content": u"**📍 环境信息**\n " + event.get_tag('environment'),
                                    "tag": "lark_md"
                                }
                            },
                            {
                                "is_short": False,
                                "text": {
                                    "content": "",
                                    "tag": "lark_md"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "content": u"**🕙 触发时间**\n " + datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S'),
                                    "tag": "lark_md"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "content": u"**📩 错误摘要**\n " + message,
                                    "tag": "lark_md"
                                }
                            }
                        ],
                        "tag": "div"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "content": u"😊 Sentry 地址：http://172.30.0.93:9000 \n🙈 系统发布流程与规范：https://cyclone.feishu.cn/docs/doccncIqdU5VExJrXb4JUo4adbb \n\n",
                            "tag": "lark_md"
                        }
                    },
                    {
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "content": u"查看告警详情",
                                    "tag": "plain_text"
                                },
                                "type": "danger",
                                "url": u"{}events/{}/".format(group.get_absolute_url(), event.id)
                            }
                        ],
                        "tag": "action"
                    }
                ],
                "header": {
                    "template": "red",
                    "title": {
                        "content": u"📢 服务告警通知",
                        "tag": "plain_text"
                    }
                }
            }
        }

        requests.post(
            url=send_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(data).encode("utf-8")
        )

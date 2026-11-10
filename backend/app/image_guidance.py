"""Non-inference photo guidance for the normal local presentation runtime.

Only exact bytes of four published project assets have predefined hints. No
filename, caption, pixel interpretation, model, external API or network is used.
"""
import hashlib

from .database import TAGS

IMAGE_PROCESSING={
    'status':'guided',
    'name':'写真のタグを自分で選ぶ',
    'mode':'manual-with-predefined-assets',
    'method':'manual-photo-tags-v1',
    'inference_enabled':False,
    'external_ai_enabled':False,
    'description':'写真の自動認識は行いません。登録済みの素材には事前に設定した候補を表示し、それ以外の写真は自分でタグを選びます。',
}

PREDEFINED={
    '7c3d10eab4ef9ce2c6ff70f6a61290c3d6cef35778d768e76f5e30949f2d8a70':('mountain','nature','cafe'),
    '57d7cc0f5deec556ecdb94180bb74f23b707da5de31340f1bf4ea0387a01814e':('cafe','food'),
    '239bd1bb1e9cd568a6a516fd1e293e9629f256a9a0e19c56e3dc6bb571ff9aac':('coast','walk'),
    'e172f70897ba56d5255dc432946052daed2dff7316023de1f976a6e6e65cdfaf':('food','games','stay'),
}


def photo_guidance(raw):
    # MOC: current output uses fixed public-asset hints, not actual AI. A future
    # external-AI adapter may replace this output boundary only after explicit
    # implementation approval; auth, consent, structured validation and saving
    # remain server-controlled. No API, SDK, key or network client exists here.
    tags=PREDEFINED.get(hashlib.sha256(raw).hexdigest(),())
    return dict(status='guided' if tags else 'manual',tags=[{'id':tag,'label':TAGS[tag]} for tag in tags],
                message='登録済み素材に設定された候補です。写真に合うタグを選んでください。' if tags else '写真の自動認識は行いません。写真に合うタグを自分で選んでください。',
                model_version=None,method='predefined-photo-tags-v1' if tags else 'manual-photo-tags-v1',inference_enabled=False)


class ImageGuidance:
    """MOC compatibility boundary; it never opens a model or starts inference."""
    session=None
    version=None
    inference_enabled=False

    @staticmethod
    def classify(_path):
        raise RuntimeError('image_inference_disabled')

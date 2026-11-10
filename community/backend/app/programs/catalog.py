PROGRAMS = (
    dict(id='n-nishi-pottery', title='自分の器を作って受け取る',
         goal='成形から絵付け、受け取りまで、一つの器の工程をたどる。',
         provider_id='ops26-provider-1', route_id='osaka-nnishi-pottery', tags=['fashion', 'cafe'],
         recommended_interval='乾燥・焼成の進み具合に合わせ、次回の日程を陶房と相談します。',
         steps=(('shape', '土を選んで成形する', '器の形と使い方を決め、手びねりで形を作る。', 3800),
                ('decorate', '絵付けと仕上げをする', '前回の器に絵付けをし、仕上がりを相談する。', 2800),
                ('receive', '器を受け取り使い方を聞く', '焼き上がりを確認し、手入れの説明を聞いて受け取る。', 1200))),
    dict(id='n-nishi-garden', title='季節の小さな鉢を育てる',
         goal='植え付け、手入れ、育ち方の振り返りを続けて学ぶ。',
         provider_id='ops26-provider-2', route_id='osaka-nnishi-garden', tags=['nature', 'walk'],
         recommended_interval='植物の状態と季節を確認しながら、次回の手入れ日を相談します。',
         steps=(('plant', '苗を選んで植える', '置き場所に合う苗を選び、鉢に植える。', 3200),
                ('care', '育ち方を見て手入れする', '前回からの変化を見て、水やりや切り戻しを学ぶ。', 2200),
                ('review', '育てた鉢を振り返る', '育ち方を確かめ、これからの手入れ計画を立てる。', 1800))),
)


def plan_id(program_id, step_id):
    return 'program-' + program_id + '-' + step_id

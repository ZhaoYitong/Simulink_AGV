import random

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

LOAD = 1  # 装船
UNLOAD = 2  # 卸船
ENTER = 1  # 入堆场
OUT = 2  # 出堆场

OUTPORT = 1  # 出港
INPORT = 2  # 入港
SHIPCYCLE = 3  # 岸桥间周转
YARDCYCLE = 4  # 场桥间周转

QC_READY = random.normalvariate(8, 1)  # 岸桥完成上一个任务到下一个任务就绪时间
QC_LIFT_DROP = random.normalvariate(1, 0.1)  # 岸桥岸侧小车提落到AGV时间
QC_TOSHIP = random.normalvariate(5, 1)  # 岸桥海侧小车装/卸箱时间

ARMG_READY = random.normalvariate(6, 1)  # 海侧场吊完成上一个任务到下一个任务就绪时间
ARMG_LIFT_DROP = random.normalvariate(1, 0.1)  # 海侧场吊提落到AGV时间
ARMG_TOYARD = random.normalvariate(4, 0.2)  # 海侧场吊移箱到指定位置时间

HOLDER_JACK = random.normalvariate(0.8, 0.02)  # 支架顶升时间

AGV_SPEED = 10  # AGV速度



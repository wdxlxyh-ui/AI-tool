#!/bin/bash
log_path="filetest.log"
log_with_date() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] - $message" >> "$log_path"
}

folder_path="/data2/fe_protocol_data/curtailment/"

# 定义原始数据的前42个字节
original_prefix="\x00\x00\x00\x00\x00\x01\x03\x00\x00\x00\x00\x01\x02\x05\x00\x01\x00\x01\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06\x05\x00\x00\x00\x01\x00\x00\x01\x01"

# 定义原始数据的后固定部分
original_suffix="\x06\x00\x00\x02\x00\x02\x04\x00\x07\x00\x01\x01\x08\x03\x06\x00\x00"

# 调用Python脚本获取输出结果
python_output=$(python3 -c "from datetime import datetime


def get_time_variables():
    # 获取当前时间
    now = datetime.now()
    # now = datetime(2024, 12, 14, 9, 33, 0)

    # 获取具体的年、月、日、时、分
    nian = now.year
    yue = now.month
    ri = now.day
    shi = now.hour
    fen = now.minute
    shi += 9

    # 处理小时和分钟
    if fen >= 30:
        shi += 1
        fen_str = '0000'
    else:
        fen_str = '0300'

    if shi >= 24:
        shi -= 24
        ri += 1

    # 定义变量并赋值
    nian_str = f'{nian // 1000:02}{nian // 100 % 10:02}'
    nianS_str = f'0{nian % 100 // 10}0{nian % 10}'
    yue_str = f'{yue // 10:02}0{yue % 10}'
    ri_str = f'{ri // 10:02}0{ri % 10}'
    shi_str = f'{shi // 10:02}0{shi % 10}'

    return nian_str, nianS_str, yue_str, ri_str, shi_str, fen_str


def insert_x(input_string):
    # 每两个数字作为一个新变量，并在每两个数字前加上\x
    new_vars = [r'\x' + input_string[i:i+2] for i in range(0, len(input_string), 2)]
    return ''.join(new_vars)


nian, nianS, yue, ri, shi, fen = get_time_variables()

output = insert_x(nian) + insert_x(nianS) + insert_x(yue) + insert_x(ri) + insert_x(shi) + insert_x(fen)


print(output)")
python_output=$(echo -n "$python_output")
log_with_date " 计划开始时间 : $python_output"


# 生成随机字节
generate_byte_strings() {
    local count=$1  
    local result="" 

    for ((i=1; i<=$count; i++)); do
        random_num=$((RANDOM % 101))  
        log_with_date "第$i个时间段计划值为： $random_num"
        hex_str=$(printf "%02x" "$random_num") 
        formatted_byte_string="\x$hex_str" 
        result+=$formatted_byte_string  
    done

    result="$count$result" 
    echo $result
}

#output=$(generate_byte_strings 6)   #循环6次，生成6个计划文件
#log_with_date "转换为十六进制后的计划值 : $output"
#file_content=$original_prefix$python_output"\x00\x00\x0"$output$original_suffix
#echo $file_content

file_path(){
    if [ ! -d "$folder_path" ]; then
        mkdir -p "$folder_path"
    fi

}

file_create(){
    date=$(date +%Y%m%d%H%M%S)
    curtailment_file_path=203_0000_01000300000000006500010011_$date.data
    echo -ne "$file_content" > "$folder_path$curtailment_file_path"

    #创建文件并写入内容
    log_with_date "文件 '$curtailment_file_path' 已创建。"
}




output=$(generate_byte_strings 6)   #循环6次，生成6个计划文件

log_with_date "转换为十六进制后的计划值 : $output"

file_content=$original_prefix$python_output"\x00\x00\x00\x00\x0"$output$original_suffix
file_path
file_create




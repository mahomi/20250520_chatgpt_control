import json
import os
from typing import Dict, Any
import sys
import re
from apply_contextual_patch import apply_patch

file_working_dir = r"M:\TEST"
output_filename = "output.txt"

def main():
    # input.txt에서 JSON 명령어 추출
    if not extract_json_commands():
        print_file("JSON 명령어 추출에 실패하여 프로그램을 종료합니다.")
        return
    
    # test()
    handler = FileHandler()

    json_filename = "input.json"
    try:
        with open(json_filename, 'r', encoding='utf-8') as f:
            cmd_data = json.load(f)
            result = handler.process_command(cmd_data)
            print_file(result)
            print(f"\n결과가 {output_filename} 파일에 저장되었습니다.")
            
    except FileNotFoundError:
        error_msg = f"파일을 찾을 수 없습니다: {json_filename}"
        print_file(error_msg)
    except json.JSONDecodeError:
        error_msg = f"JSON 형식이 올바르지 않습니다: {json_filename}"
        print_file(error_msg)
    except Exception as e:
        error_msg = f"오류 발생: {str(e)}"
        print_file(error_msg)

def test():
    handler = FileHandler()
    
    # 테스트 명령어들
    test_commands = [
        '{"cmd":"file-list","message":"파일목록을 살펴보겠습니다"}',
        '{"cmd":"file-open test.txt","message":"test.txt을 열어보겠습니다"}',
        # '{"cmd":"file-new test.txt","message":"test.txt을 새 파일로 저장합니다","content":"이것은 테스트 파일의 내용입니다."}',
        '{"cmd":"file-save test.txt","message":"test.txt을 저장합니다","content":"이것은 테스트 파일의 내용입니다."}',
        '{"cmd":"file-apply-diff test.txt","message":"test.txt에 차이점을 적용합니다","content":"unified_diff"}'
    ]
    
    for cmd_json in test_commands:
        cmd_data = json.loads(cmd_json)
        result = handler.process_command(cmd_data)
        print(result)
        print("-" * 50)


class FileHandler:
    def __init__(self):
        self.commands = {
            "file-list": self.list_files,
            "file-open": self.open_file,
            # "file-new": self.save_file,
            "file-save": self.save_file,
            "file-apply-diff": self.apply_diff
        }
        self.command_data = {}
        # 작업 디렉토리가 없으면 생성
        if not os.path.exists(file_working_dir):
            os.makedirs(file_working_dir)

    def process_command(self, command_data: Dict[str, Any]) -> str:
        try:
            self.command_data = command_data
            cmd = command_data.get("cmd", "")
            message = command_data.get("message", "")
            
            # message는 콘솔에만 출력
            print(message)
            
            # 명령어 파싱
            cmd_parts = cmd.split()
            base_cmd = cmd_parts[0]
            
            if base_cmd in self.commands:
                # 명령어 실행
                result = self.commands[base_cmd](cmd_parts[1:] if len(cmd_parts) > 1 else [])
                return result
            else:
                return f"알 수 없는 명령어입니다: {base_cmd}"
                
        except Exception as e:
            return f"오류 발생: {str(e)}"

    def list_files(self, args: list) -> str:
        try:
            files = os.listdir(file_working_dir)
            return f"{file_working_dir} 디렉토리의 파일 목록:\n" + "\n".join(files)
        except Exception as e:
            return f"파일 목록을 가져오는 중 오류 발생: {str(e)}"

    def open_file(self, args: list) -> str:
        if not args:
            return "파일 이름이 필요합니다."
        
        filename = os.path.join(file_working_dir, args[0])
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"파일 내용:\n{content}"
        except Exception as e:
            return f"파일을 여는 중 오류 발생: {str(e)}"

    def save_file(self, args: list) -> str:
        if not args:
            return "파일 이름이 필요합니다."
        
        filename = os.path.join(file_working_dir, args[0])
        try:
            content = self.command_data.get("content", "")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"파일이 성공적으로 저장되었습니다: {filename}"
        except Exception as e:
            return f"파일을 저장하는 중 오류 발생: {str(e)}"
    
    def apply_diff(self, args: list) -> str:
        if not args:
            return "파일 이름이 필요합니다."
        
        filename = os.path.join(file_working_dir, args[0])
        try:
            # 임시 패치 파일 생성
            patch_content = self.command_data.get("content", "")
            patch_file = os.path.join(file_working_dir, "temp.patch")
            with open(patch_file, 'w', encoding='utf-8') as f:
                f.write(patch_content)
            
            # 패치 적용
            apply_patch(filename, patch_file)
            
            # 임시 파일 삭제
            os.remove(patch_file)
            
            # 변경된 파일 내용 읽기
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return f"위의 변경사항을 적용하여, {filename} 파일이 아래와 같이 성공적으로 수정되었습니다. 변경사항이 제대로 적용되었는지 확인하고 잘못된 부분은 다시 file-apply-diff 명령을 호출해 수정해라.\n파일 내용:\n{content}"
        except Exception as e:
            return f"파일에 변경사항 적용 중 오류 발생: {str(e)}"
        
        



def extract_json_commands(input_txt: str = "input.txt", output_json: str = "input.json") -> bool:
    """
    input.txt 파일에서 JSON 코드 블록 안의 내용을 추출하여 input.json 파일로 저장합니다.
    
    Args:
        input_txt (str): 입력 파일 이름
        output_json (str): 출력 JSON 파일 이름
        
    Returns:
        bool: 성공적으로 처리되었으면 True, 실패하면 False
    """
    try:
        # input.txt 파일 읽기
        with open(input_txt, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # JSON 코드 블록 찾기
        json_blocks = re.findall(r'```json\n(.*?)\n```', content, re.DOTALL)
        
        if not json_blocks:
            print(f"input.txt에서 JSON 코드 블록을 찾을 수 없습니다.")
            return False
        
        # 첫 번째 JSON 블록의 내용을 저장
        json_content = json_blocks[0].strip()
        
        # JSON 형식 검증
        try:
            json.loads(json_content)
        except json.JSONDecodeError:
            print(f"잘못된 JSON 형식입니다.")
            return False
        
        # input.json 파일로 저장
        with open(output_json, 'w', encoding='utf-8') as f:
            f.write(json_content)
        
        print(f"JSON 코드 블록이 {output_json}에 저장되었습니다.")
        return True
        
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {input_txt}")
        return False
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return False


def print_file(message: str, append: bool = False) -> None:
    """
    메시지를 콘솔에 출력하고 output.txt 파일에도 기록합니다.
    
    Args:
        message (str): 출력할 메시지
        append (bool): True이면 파일에 추가, False이면 파일을 새로 생성
    """
    # 콘솔에 출력
    print(message)
    
    # 파일에 기록
    mode = 'a' if append else 'w'
    with open(output_filename, mode, encoding='utf-8') as f:
        f.write(message + '\n')


if __name__ == "__main__":
    main() 
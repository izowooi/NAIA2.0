import random
import re
from typing import List
from .prompt_context import PromptContext
from .wildcard_manager import WildcardManager

class WildcardProcessor:
    def __init__(self, wildcard_manager: WildcardManager):
        self.wildcard_manager = wildcard_manager

    def expand_tags(self, tag_list: List[str], context: PromptContext) -> List[str]:
        """
        태그 리스트를 받아 리스트 내의 모든 와일드카드를 확장합니다.
        이것이 다른 모듈에서 호출할 기본 진입점(entry-point)이 됩니다.
        """
        expanded_list = []
        for tag in tag_list:
            expanded_list.extend(self._expand_recursive(tag, context))
        return expanded_list

    def _expand_recursive(self, tag: str, context: PromptContext, depth=0) -> List[str]:
        """하나의 태그를 재귀적으로 확장합니다."""
        if depth > 10: return [tag]

        if tag.startswith('<') and tag.endswith('>'):
            wildcard_name = tag[1:-1]
            
            # 인라인 와일드카드 처리
            if '|' in wildcard_name:
                options = wildcard_name.split('|')
                chosen_option = random.choice(options).strip()
                return self._expand_recursive(chosen_option, context, depth + 1)

            # 파일 기반 와일드카드 처리 - <태그명> 형태는 기존 로직 유지
            line = self._get_wildcard_line(wildcard_name, context)
            if line is None: return [tag]
            
            resolved_tags = self._expand_recursive(line, context, depth + 1)
            
            final_tags_in_place = []
            for resolved_tag in resolved_tags:
                sub_tags = [t.strip() for t in resolved_tag.split(',')]
                tags_to_keep = [t[1:] for t in sub_tags if t.startswith('*')]
                tags_to_append = [t for t in sub_tags if not t.startswith('*')]

                if tags_to_keep:
                    final_tags_in_place.extend(tags_to_keep)
                    context.global_append_tags.extend(tags_to_append)
                elif tags_to_append:
                    final_tags_in_place.append(tags_to_append[0])
                    context.global_append_tags.extend(tags_to_append[1:])
            
            return final_tags_in_place if final_tags_in_place else []
        
        # 복합 와일드카드 처리 (__...__)
        if '__' in tag:
            parts = re.split(r'(__.*?__)', tag)
            result_parts = []
            
            for part in parts:
                if not part:
                    continue
                    
                if part.startswith('__') and part.endswith('__'):
                    # __태그명__ 형태: global_append_tags 없이 현재 위치에 일괄 나열
                    wildcard_name = part[2:-2]
                    line = self._get_wildcard_line(wildcard_name, context)
                    if line is not None:
                        expanded_parts = self._expand_recursive(line, context, depth + 1)
                        # 모든 결과를 현재 위치에 콤마로 연결
                        all_tags = []
                        for expanded_part in expanded_parts:
                            sub_tags = [t.strip() for t in expanded_part.split(',')]
                            all_tags.extend(sub_tags)
                        result_parts.append(', '.join(all_tags))
                    else:
                        result_parts.append(part)  # 확장 실패시 원본 유지
                else:
                    result_parts.append(part)
            
            return [''.join(result_parts)]

        return [tag]

    def _get_wildcard_line(self, wildcard_name: str, context: PromptContext) -> str | None:
        """WildcardManager에서 와일드카드 내용을 가져옵니다. 순차/종속 모드를 처리합니다."""
        is_sequential = wildcard_name.startswith('*')
        is_observer = wildcard_name.startswith('$')

        if is_sequential:
            wildcard_name = wildcard_name[1:]
        elif is_observer:
            try:
                master_name, slave_name = wildcard_name[1:].split(':', 1)
                wildcard_name = slave_name
            except ValueError:
                print(f"경고: 잘못된 종속 와일드카드 구문입니다: {wildcard_name}")
                return None
        
        lines = self.wildcard_manager.wildcard_dict_tree.get(wildcard_name)
        if not lines:
            print(f"경고: 와일드카드 '{wildcard_name}'을 찾을 수 없습니다.")
            return None
        
        chosen_line = ""
        total_lines = len(lines)
        
        if is_sequential:
            counter = context.sequential_counters.get(wildcard_name, 0)
            chosen_line = lines[counter % total_lines]
            context.sequential_counters[wildcard_name] = counter + 1
            # [상태 관찰] 순차 와일드카드 상태 기록
            context.wildcard_state[wildcard_name] = {'current': counter % total_lines + 1, 'total': total_lines}

        elif is_observer:
            # 🔧 [수정] Master/Slave 의존성 로직 개선
            master_counter = context.sequential_counters.get(master_name, 0)
            
            # Master 와일드카드의 길이를 가져와서 사이클 계산
            master_lines = self.wildcard_manager.wildcard_dict_tree.get(master_name, [])
            master_total = len(master_lines) if master_lines else 1
            
            # Master가 완전한 사이클을 몇 번 완료했는지 계산
            # master_counter는 이미 1 증가된 상태이므로 -1 후 계산
            completed_master_cycles = (master_counter - 1) // master_total if master_counter > 0 else 0
            
            # Slave는 master의 완전한 사이클 완료 횟수에 따라 진행
            slave_index = completed_master_cycles % total_lines
            chosen_line = lines[slave_index]
            
            # [상태 관찰] 종속 와일드카드 상태 기록
            context.wildcard_state[wildcard_name] = {'current': slave_index + 1, 'total': total_lines, 'master_cycles': completed_master_cycles}
            
        else: # 일반 무작위 모드
            chosen_line = random.choice(lines)
        
        context.wildcard_history.setdefault(wildcard_name, []).append(chosen_line)
        return chosen_line
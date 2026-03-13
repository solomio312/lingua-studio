import re
import json
import copy
from typing import Any

from lxml import etree
from xml.sax.saxutils import escape as xml_escape

from .utils import (
    ns, uid, trim, sorted_mixed_keys, open_file, css_to_xpath, create_xpath)
from .config import get_config


def get_string(element, remove_ns=False):
    element.text = element.text or ''  # prevent auto-closing empty elements
    markup = trim(etree.tostring(
        element, encoding='utf-8', with_tail=False).decode('utf-8'))
    return re.sub(r'\sxmlns="[^"]+"', '', markup) if remove_ns else markup


def get_name(element):
    return etree.QName(element).localname


class Element:
    def __init__(self, element, page_id=None, ignored=False):
        self.element = element
        self.page_id = page_id
        self.ignored = ignored

        self.placeholder: tuple = ()
        self.reserve_elements = []
        self.original = []
        self.column_gap = None

        self.position = None
        self.target_direction = None
        self.translation_lang = None
        self.original_color = None
        self.translation_color = None

        self.remove_pattern = None
        self.reserve_pattern = None

        self.registry = {}
        self.id_start = 0

    def set_registry(self, registry):
        self.registry = registry

    def set_id_start(self, id_start):
        self.id_start = id_start

    def _element_copy(self):
        return copy.deepcopy(self.element)

    def set_ignored(self, ignored):
        self.ignored = ignored

    def set_placeholder(self, placeholder):
        self.placeholder = placeholder

    def set_column_gap(self, values):
        self.column_gap = values

    def set_position(self, position):
        self.position = position

    def set_target_direction(self, direction):
        self.target_direction = direction

    def set_translation_lang(self, lang):
        self.translation_lang = lang

    def set_original_color(self, color):
        self.original_color = color

    def set_translation_color(self, color):
        self.translation_color = color

    def set_remove_pattern(self, pattern):
        self.remove_pattern = pattern

    def set_reserve_pattern(self, pattern):
        self.reserve_pattern = pattern

    def get_name(self):
        return None

    def get_attributes(self):
        return None

    def delete(self):
        pass

    def get_raw(self):
        raise NotImplementedError()

    def get_text(self):
        raise NotImplementedError()

    def get_content(self):
        raise NotImplementedError()

    def add_translation(self, translation=None):
        raise NotImplementedError()

    def get_translation(self):
        pass


class SrtElement(Element):
    def get_raw(self):
        return self.element[2]

    def get_text(self):
        return self.get_raw()

    def get_content(self):
        return self.get_text()

    def add_translation(self, translation=None):
        if translation is not None:
            if self.position == 'only':
                self.element[2] = translation
            elif self.position in ('below', 'right'):
                self.element[2] += '\n%s' % translation
            else:
                self.element[2] = '%s\n%s' % (translation, self.element[2])

    def get_translation(self):
        return '\n'.join(self.element)


class PgnElement(Element):
    def get_raw(self):
        return self.element[0]

    def get_text(self):
        return self.get_raw().strip('{}')

    def get_content(self):
        return self.get_text()

    def add_translation(self, translation=None):
        if translation is not None:
            if self.position == 'only':
                self.element[1] = translation
            else:
                content = (self.get_content(), translation)
                if self.position not in ('below', 'right'):
                    content = tuple(reversed(content))
                self.element[1] = ' | '.join(content)

    def get_translation(self):
        if self.element[1] is None:
            return self.element[0]
        return '{%s}' % self.element[1]


class MetadataElement(Element):
    def get_raw(self):
        return self.element.content

    def get_text(self):
        return self.element.content

    def get_content(self):
        return self.element.content

    def add_translation(self, translation=None):
        if translation is not None and translation != self.get_content() \
                and not self.ignored:
            if self.position == 'only':
                self.element.content = translation
            elif self.position in ['above', 'left']:
                self.element.content = '%s %s' % (
                    translation, self.element.content)
            else:
                self.element.content = '%s %s' % (
                    self.element.content, translation)


class TocElement(Element):
    def get_raw(self):
        return self.element.title

    def get_text(self):
        return self.element.title

    def get_content(self):
        return self.element.title

    def add_translation(self, translation=None):
        if translation is not None:
            items = [self.element.title, translation]
            self.element.title = items[-1] if self.position == 'only' else \
                ' '.join(reversed(items) if self.position in ('above', 'left')
                         else items)


class PageElement(Element):
    def get_name(self):
        return get_name(self.element)

    def get_raw(self):
        return get_string(self.element, True)

    def get_text(self):
        return trim(''.join(self.element.itertext()))

    def get_attributes(self):
        attributes = dict(self.element.attrib.items())
        return json.dumps(attributes) if attributes else None

    def _safe_remove(self, element, replacement=''):
        previous, parent = element.getprevious(), element.getparent()
        if previous is not None:
            previous.tail = (previous.tail or '') + replacement
            previous.tail += (element.tail or '')
        else:
            parent.text = (parent.text or '') + replacement
            parent.text += (element.tail or '')
        element.tail = None
        parent.remove(element)

    def get_content(self):
        element_copy = self._element_copy()
        if self.remove_pattern is not None:
            for noise in element_copy.xpath(
                    self.remove_pattern, namespaces=ns):
                self._safe_remove(noise)
        elements = []
        if self.reserve_pattern is not None:
            elements = element_copy.xpath(self.reserve_pattern, namespaces=ns)
        for eid, element in enumerate(elements):
            unique_id = self.id_start + eid
            replacement = self.placeholder[0].format(format(unique_id, '05'))
            if get_name(element) in ('sub', 'sup'):
                parent = element.getparent()
                if parent is not None and get_name(parent) == 'a' and \
                        parent.text is None and element.tail is None and \
                        len(parent.getchildren()) == 1:
                    elements[eid] = element = parent
            
            # Use global registry
            self.registry[unique_id] = get_string(element, True)
            self._safe_remove(element, replacement)
        return trim(''.join(element_copy.itertext()))

    def _polish_translation(self, translation):
        translation = translation.replace('\n', '<br/>')
        # Condense consecutive letters to a maximum of four.
        return re.sub(r'((\w)\2{3})\2*', r'\1', translation)

    def _create_new_element(
            self, name, content='', copy_attrs=True, excluding_attrs=[]):
        # Copy the namespaces from the original namespaces to the new ones.
        namespaces = ' '.join(
            'xmlns%s="%s"' % ('' if name is None else ':' + name, value)
            for name, value in self.element.nsmap.items())
        new_element = etree.XML('<{0} {1}>{2}</{0}>'.format(
            name, namespaces, trim(content)))
        # Preserve all attributes from the original element.
        if copy_attrs:
            for name, value in self.element.items():
                if (name == 'id' and self.position != 'only') or \
                        name in excluding_attrs:
                    continue
                new_element.set(name, value)
        new_element.set('dir', self.target_direction or 'auto')
        if self.translation_lang is not None:
            new_element.set('lang', self.translation_lang)
        if self.translation_color is not None:
            new_element.set('style', 'color:%s' % self.translation_color)
        return new_element

    def add_translation(self, translation=None):
        # self.element.tail = None  # Make sure the element has no tail
        if self.original_color is not None:
            for element in self.element.iter():
                if element.text is not None or len(list(element)) > 0:
                    element.set('style', 'color:%s' % self.original_color)
        if translation is None:
            if self.position in ('left', 'right'):
                self.element.addnext(self._create_table())
                self._safe_remove(self.element)
            elif self.position == 'only':
                # Remove original when position is 'only' even if no translation
                # This prevents duplication when alignment fails
                pass  # Just leave as-is if no translation available for 'only' position
            return
        # Escape the markups (<m id=1 />) to replace escaped markups.
        # Escape the markups (<m id=1 />) to replace escaped markups.
        translation = xml_escape(translation)
        
        # Use regex to replace all placeholders using global registry
        def replace_match(match):
            try:
                # Try to get the named group 'id'
                rid = int(match.group('id'))
            except (IndexError, ValueError):
                # Fallback if something goes wrong (shouldn't happen with correct pattern)
                return match.group(0)
            return self.registry.get(rid, match.group(0))

        # Pattern matches [[id_(\d+)]] (escaped)
        # We inject a named group (?P<id>\d+) so we can find it regardless of other groups.
        pattern = self.placeholder[1].format(r'(?P<id>\d+)')
        translation = re.sub(pattern, replace_match, translation)
        
        # Fallback: also try to match [[id_...]] specifically, in case LLM hallucinated brackets
        # or if the engine uses {{...}} but returned [[...]]
        fallback_pattern = r'\[\[id_(?P<id>\d+)\]\]'
        translation = re.sub(fallback_pattern, replace_match, translation)

        # Cleanup any residual [[t1]], [[t2]], etc. markers that LLM might have left
        # These are prompt instructions for tag masking that should never appear in final output
        translation = re.sub(r'\[\[t\d+\]\]', '', translation)

        translation = self._polish_translation(translation)

        element_name = get_name(self.element)
        new_element = self._create_new_element(element_name, translation)

        # Add translation for table elements.
        group_elements = ('li', 'th', 'td', 'caption')
        if element_name in group_elements:
            if self.position == 'only':
                self.element.addnext(new_element)
                self._safe_remove(self.element)
            new_element = self._create_new_element(
                'span', translation, excluding_attrs=['class'])
            if self.position in ['left', 'above']:
                if self.element.text is not None:
                    if self.position == 'above':
                        br = etree.SubElement(self.element, 'br')
                        br.tail = self.element.text
                        self.element.insert(0, br)
                    else:
                        new_element.tail = ' ' + self.element.text
                    self.element.text = None
                self.element.insert(0, new_element)
            else:
                if self.position == 'below':
                    self.element.append(etree.SubElement(self.element, 'br'))
                else:
                    children = self.element.getchildren()
                    if len(children) > 0:
                        element = children[-1]
                        if element.tail is not None:
                            element.tail += ' '
                        else:
                            element.tail = ' '
                    else:
                        self.element.text += ' '
                self.element.append(new_element)
            return

        text_elements = (
            'a', 'em', 'strong', 'small', 's', 'cite', 'q', 'time', 'samp',
            'i', 'b', 'u', 'mark', 'span', 'data', 'del', 'ins')
        is_text_element = element_name in text_elements

        # Add translation for left or right position.
        if self.position in ('left', 'right') and not is_text_element:
            self.element.addnext(self._create_table(new_element))
            self._safe_remove(self.element)
            return

        # Add translation for line breaks.
        line_break_tag = '{%s}br' % ns['x']
        original_br_list = list(self.element.iterdescendants(line_break_tag))
        translation_br_list = list(new_element.iterchildren(line_break_tag))
        if (len(original_br_list) == len(translation_br_list) > 0) and \
                self.position in ('below', 'above'):
            self._add_translation_for_line_breaks(
                new_element, original_br_list, translation_br_list)
            return

        parent_element = self.element.getparent()
        is_table_descendant = parent_element is not None and \
            get_name(parent_element) in group_elements

        if self.position == 'only':
            self.element.addnext(new_element)
            self._safe_remove(self.element)
            return

        # new_element.tag = 'span'
        if self.position in ('left', 'above'):
            # Add translation next to the element.
            self.element.addprevious(new_element)
            # # Add translation at the start of the element.
            # new_element.tail = self.element.text
            # self.element.text = None
            # self.element.insert(0, etree.SubElement(self.element, 'br'))
            # self.element.insert(0, new_element)
            if is_text_element and is_table_descendant:
                new_element.addnext(etree.SubElement(self.element, 'br'))
            elif is_text_element:
                new_element.tail = ' '
        else:
            # Add translation next to the element.
            self.element.addnext(new_element)
            # # Added translation at the end of the element.
            # self.element.append(etree.SubElement(self.element, 'br'))
            # self.element.append(new_element)
            if is_text_element and is_table_descendant:
                self.element.addnext(etree.SubElement(self.element, 'br'))
            elif is_text_element:
                if self.element.tail is not None:
                    new_element.tail = self.element.tail
                self.element.tail = ' '

    def _add_translation_for_line_breaks(
            self, new_element, original_br_list, translation_br_list):
        text = new_element.text
        tail = None
        if self.position == 'below':
            for index, br in enumerate(original_br_list):
                translation_br = translation_br_list[index]
                wrapper = self._create_new_element(
                    'span', copy_attrs=False, excluding_attrs=['class'])
                # Get preceding siblings in reverse document order.
                for sibling in translation_br.itersiblings(preceding=True):
                    if get_name(sibling) == 'br':
                        break
                    wrapper.insert(0, sibling)
                wrapper.text = text if index == 0 else tail
                tail = translation_br.tail
                if wrapper.text or len(list(wrapper)) > 0:
                    new_br = etree.SubElement(self.element, 'br')
                    br.addprevious(new_br)
                    new_br.addnext(wrapper)
                # Handle the last br element in the translation simultaneously.
                if br == original_br_list[-1]:
                    # Ignore the last barely br element.
                    if translation_br.getnext() is None and (
                            tail is None or tail.strip() == ''):
                        continue
                    wrapper = self._create_new_element(
                        'span', copy_attrs=False, excluding_attrs=['class'])
                    for sibling in translation_br.itersiblings():
                        wrapper.append(sibling)
                    wrapper.text = tail
                    new_br = etree.SubElement(self.element, 'br')
                    self.element.append(new_br)
                    new_br.addnext(wrapper)
        else:
            for index, br in enumerate(original_br_list):
                translation_br = translation_br_list[index]
                wrapper = self._create_new_element(
                    'span', copy_attrs=False, excluding_attrs=['class'])
                for sibling in translation_br.itersiblings():
                    if get_name(sibling) == 'br':
                        break
                    wrapper.insert(0, sibling)
                wrapper.text = translation_br.tail
                if wrapper.text or len(list(wrapper)) > 0:
                    new_br = etree.SubElement(self.element, 'br')
                    new_br.tail = br.tail
                    br.tail = None
                    br.addnext(new_br)
                    new_br.addprevious(wrapper)
                if br == original_br_list[0]:
                    wrapper = self._create_new_element(
                        'span', copy_attrs=False, excluding_attrs=['class'])
                    if translation_br.getprevious() is None and (
                            text is None or text.strip() == ''):
                        continue
                    for sibling in translation_br.itersiblings(preceding=True):
                        wrapper.insert(0, sibling)
                    wrapper.text = new_element.text
                    new_br = etree.SubElement(self.element, 'br')
                    new_br.tail = self.element.text
                    self.element.text = None
                    self.element.insert(0, new_br)
                    new_br.addprevious(wrapper)

    def _create_table(self, translation=None):
        # table = self.element.makeelement('table', attrib={'width': '100%'})
        original = self._element_copy()
        table = etree.XML(
            '<table xmlns="{}" width="100%"></table>'.format(ns['x']))
        tr = etree.SubElement(table, 'tr')
        td_left = etree.SubElement(tr, 'td', attrib={'valign': 'top'})
        td_middle = etree.SubElement(tr, 'td')
        td_right = etree.SubElement(tr, 'td', attrib={'valign': 'top'})
        if self.column_gap is None:
            td_left.set('width', '45%')
            td_middle.set('width', '10%')
            td_right.set('width', '45%')
        else:
            unit, value = self.column_gap
            if unit == 'percentage':
                width = '%s%%' % round((100 - value) / 2)
                td_left.set('width', width)
                td_middle.set('width', '%s%%' % value)
                td_right.set('width', width)
            else:
                td_left.set('width', '50%')
                td_middle.text = '\xa0' * value
                td_right.set('width', '50%')
        if self.position == 'left':
            if translation is not None:
                td_left.append(translation)
            td_right.append(original)
        if self.position == 'right':
            td_left.append(original)
            if translation is not None:
                td_right.append(translation)
        return table


class Extraction:
    def __init__(
            self, pages, priority_rules, rule_mode, filter_scope, filter_rules,
            ignore_rules, spine_order=None):
        self.pages = pages
        self.priority_rules = priority_rules
        self.rule_mode = rule_mode
        self.filter_scope = filter_scope
        self.filter_rules = filter_rules
        self.ignore_rules = ignore_rules
        self.spine_order = spine_order  # Optional: list of hrefs in reading order

        # Smart HTML Merge config
        from lingua.core.config import get_config
        self.smart_html_merge = get_config().get('smart_html_merge', False)
        # Structural HTML tags that should act as boundaries, extracting as a single block 
        # to preserve context for inline spans/ems/strongs inside them.
        self.block_elements = {
            'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
            'td', 'th', 'li', 'blockquote', 'caption', 'dt', 'dd', 'figcaption'
        }

        self.priority_patterns = []
        self.filter_patterns = []
        self.ignore_patterns = []
        self.priority_tags = set(['p', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote'])
        self.ignore_tags = set(['pre', 'code'])

        self.load_priority_patterns()
        self.load_filter_patterns()
        self.load_ignore_patterns()

    def load_priority_patterns(self):
        default_selectors = [
            'p', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote']
        self.priority_patterns = css_to_xpath(
            default_selectors + self.priority_rules)
        # Add to priority_tags for fast paths
        for rule in self.priority_rules:
            if re.match(r'^[a-zA-Z0-9]+$', rule):
                self.priority_tags.add(rule.lower())

    def load_filter_patterns(self):
        default_filter_rules = (
            r'^[-\d\s\.\'\\"‘’“”,=~!@#$%^&º*|≈<>?/`—…+:–_(){}[\]]+$',)
        patterns = [re.compile(rule) for rule in default_filter_rules]
        for rule in self.filter_rules:
            if self.rule_mode == 'normal':
                rule = re.compile(re.escape(rule), re.I)
            elif self.rule_mode == 'case':
                rule = re.compile(re.escape(rule))
            else:
                rule = re.compile(rule)
            patterns.append(rule)
        self.filter_patterns = patterns

    def load_ignore_patterns(self):
        default_selectors = ['pre', 'code']
        self.ignore_patterns = css_to_xpath(
            default_selectors + self.ignore_rules)
        # Add to ignore_tags for fast paths
        for rule in self.ignore_rules:
            if re.match(r'^[a-zA-Z0-9]+$', rule):
                self.ignore_tags.add(rule.lower())

    def get_sorted_pages(self):
        pages = []
        pattern = re.compile(r'\.(xhtml|html|htm|xml|xht)$')
        for page in self.pages:
            if isinstance(page.data, etree._Element) \
                    and pattern.search(page.href):
                pages.append(page)
        if self.spine_order:
            # Sort by spine order (reading order from OPF)
            spine_index = {href: i for i, href in enumerate(self.spine_order)}
            return sorted(pages, key=lambda page: spine_index.get(
                page.href, len(spine_index)))
        return sorted(pages, key=lambda page: sorted_mixed_keys(page.href))

    def get_elements(self):
        elements = []
        pages = self.get_sorted_pages()
        for i, page in enumerate(pages):
            body = page.data.find('./x:body', namespaces=ns)
            if body is None:
                body = page.data.find('.//body')
            
            if body is not None:
                try:
                    extracted = self.extract_elements(page.id, body)
                    elements.extend(extracted)
                except Exception as ex:
                    logging.exception(f"Error extracting elements from page {page.href}")
            else:
                logging.warning(f"Body not found on page {page.href}")
        
        return list(filter(self.filter_content, elements))

    def is_priority(self, element):
        tag = get_name(element).lower()
        if tag in self.priority_tags:
            return True
        for pattern in self.priority_patterns:
            try:
                if element.xpath(pattern, namespaces=ns):
                    return True
            except: pass
        return False

    def need_ignore(self, element):
        tag = get_name(element).lower()
        if tag in self.ignore_tags:
            return True
        for pattern in self.ignore_patterns:
            try:
                if element.xpath(pattern, namespaces=ns):
                    return True
            except: pass
        return False

    def _contains_block_elements(self, element):
        for descendant in element.iterdescendants():
            if get_name(descendant) in self.block_elements:
                return True
        return False

    def extract_elements(self, page_id, root):
        """Iterative version of extract_elements using a stack to prevent stack overflow crashes."""
        elements = []
        # Stack stores (current_node, current_depth)
        stack = [(root, 0)]
        
        while stack:
            node, depth = stack.pop()
            
            if depth > 500: # Safety cap
                continue
                
            if self.need_ignore(node):
                if node != root: # Don't record root as ignored unless it's a child
                    elements.append(PageElement(node, page_id, True))
                continue
            
            # SMART MERGE: Block-level extraction
            if self.smart_html_merge and get_name(node) in self.block_elements:
                has_text = any(trim(r_text) != '' for r_text in node.itertext())
                if has_text and not self._contains_block_elements(node):
                    elements.append(PageElement(node, page_id, False))
                    continue # Don't process children

            # Check if this node has direct content or priority
            node_has_content = False
            if self.is_priority(node) or (node.text is not None and trim(node.text) != ''):
                node_has_content = True
            else:
                # Check children for tails or priority
                for child in node.findall('./*'):
                    if self.is_priority(child) or (child.tail is not None and trim(child.tail) != ''):
                        node_has_content = True
                        break
            
            if node_has_content and node != root:
                elements.append(PageElement(node, page_id, self.need_ignore(node)))
            else:
                # Add children to stack in reverse order to maintain original processing order
                children = list(node.findall('./*'))
                for child in reversed(children):
                    stack.append((child, depth + 1))
        
        if not elements:
            return [PageElement(root, page_id, self.need_ignore(root))]
        
        # Note: Iterative extraction might need result reversal/sorting if order matters,
        # but stack+reversed children preserves order.
        return elements

    def filter_content(self, element):
        # Ignore the element contains empty content
        content = element.get_text()
        if content == '':
            return False
        for entity in ('&lt;', '&gt;'):
            content = content.replace(entity, '')
        for pattern in self.filter_patterns:
            if pattern.search(content):
                element.set_ignored(True)
        # Filter HTML according to the rules
        if self.filter_scope == 'html':
            markup = element.get_raw()
            for pattern in self.filter_patterns:
                if pattern.search(markup):
                    element.set_ignored(True)
        return True


class ElementHandler:
    def __init__(self, placeholder, separator, position):
        if isinstance(placeholder, str):
            # Convert string placeholder to tuple with regex pattern
            # e.g. '[[id_{}]]' -> ('[[id_{}]]', r'\[\[id_{}\]\]')
            escaped = re.escape(placeholder)
            # Replace escaped {} with {} so format() can inject the ID regex
            regex_fmt = escaped.replace(re.escape('{}'), '{}')
            self.placeholder = (placeholder, regex_fmt)
        else:
            self.placeholder = placeholder
        self.separator = separator
        self.position = position

        self.merge_length = 0
        self.target_direction = None

        self.translation_lang = None
        self.original_color = None
        self.translation_color = None
        self.column_gap = None

        self.remove_pattern = None
        self.reserve_pattern = None

        self.elements = {}
        self.originals = []

    def set_merge_length(self, length):
        self.merge_length = length

    def get_merge_length(self):
        return self.merge_length

    def set_target_direction(self, direction):
        self.target_direction = direction

    def set_translation_lang(self, lang):
        self.translation_lang = lang

    def set_original_color(self, color):
        self.original_color = color

    def set_translation_color(self, color):
        self.translation_color = color

    def set_column_gap(self, values):
        if isinstance(values, tuple) and len(values) == 2:
            self.column_gap = values

    def load_remove_rules(self, rules=[]):
        default_rules = ('rt', 'rp')
        self.remove_pattern = create_xpath(default_rules + tuple(rules))

    def load_reserve_rules(self, rules=[]):
        # Reserve the <br> element instead of using a line break to prevent
        # conflicts with the mechanism of merge translation.
        default_rules = (
            'img', 'code', 'br', 'hr', 'sub', 'sup', 'kbd', 'abbr', 'wbr',
            'var', 'canvas', 'svg', 'script', 'style')
        self.reserve_pattern = create_xpath(default_rules + tuple(rules))

    def prepare_original(self, elements):
        count = 0
        for oid, element in enumerate(elements):
            element.set_placeholder(self.placeholder)
            element.set_position(self.position)
            element.set_target_direction(self.target_direction)
            element.set_translation_lang(self.translation_lang)
            element.set_original_color(self.original_color)
            element.set_translation_color(self.translation_color)
            if self.column_gap is not None:
                element.set_column_gap(self.column_gap)
            element.set_remove_pattern(self.remove_pattern)
            element.set_reserve_pattern(self.reserve_pattern)
            raw = element.get_raw()
            content = element.get_content()
            # Make sure the element does not contain empty content because it
            # may only contain ignored elements.
            if content.strip() == '':
                element.set_ignored(True)
            md5 = uid('%s%s' % (oid, content))
            attrs = element.get_attributes()
            if not element.ignored:
                self.elements[count] = element
                count += 1
            self.originals.append((
                oid, md5, raw, content, element.ignored, attrs,
                element.page_id))
        return self.originals

    def prepare_translation(self, paragraphs):
        translations = {}
        for paragraph in paragraphs:
            translations[paragraph.original] = paragraph.translation
        return translations

    def add_translations(self, paragraphs):
        translations = self.prepare_translation(paragraphs)
        for eid, element in self.elements.copy().items():
            if element.ignored:
                element.add_translation()
                continue
            original = element.get_content()
            translation = translations.get(original)
            if translation is None:
                element.add_translation()
                continue
            element.add_translation(translation)
            self.elements.pop(eid)


class ElementHandlerMerge(ElementHandler):
    def _is_terminator(self, text):
        return text.strip().endswith(('.', '!', '?', '"', '”', '’', "'"))

    def _flush_buffer(self, buffer, oid):
        if not buffer:
            return
        raw = ''.join(b[0] + self.separator for b in buffer)
        txt = ''.join(b[1] for b in buffer)
        md5 = uid('%s%s' % (oid, txt))
        md5 = uid('%s%s' % (oid, txt))
        self.originals.append((oid, md5, raw, txt, False))

    def _find_best_split_index(self, buffer, current_length):
        acc_len = 0
        for i in range(len(buffer) - 1, -1, -1):
            content = buffer[i][1]
            if self._is_terminator(content):
                batch_len = current_length - acc_len
                if batch_len > self.merge_length * 0.5:
                    return i + 1
            acc_len += len(content)
        return -1

    def prepare_original(self, elements):
        oid = 0
        buffer = []
        current_length = 0
        
        # Global registry for this batch
        self.registry = {}
        global_counter = 0

        for eid, element in enumerate(elements):
            self.elements[eid] = element
            if element.ignored:
                continue
            
            element.set_registry(self.registry)
            element.set_id_start(global_counter)
            
            element.set_placeholder(self.placeholder)
            element.set_position(self.position)
            element.set_target_direction(self.target_direction)
            element.set_translation_lang(self.translation_lang)
            element.set_original_color(self.original_color)
            element.set_translation_color(self.translation_color)
            if self.column_gap is not None:
                element.set_column_gap(self.column_gap)
            element.set_remove_pattern(self.remove_pattern)
            element.set_reserve_pattern(self.reserve_pattern)

            code = element.get_raw()
            content = element.get_content()
            global_counter = len(self.registry)
            content += self.separator

            if current_length + len(content) > self.merge_length:
                # Try to find a good split point
                split_index = self._find_best_split_index(buffer, current_length)

                if split_index == -1:
                    # Try extending
                    if self._is_terminator(content) and \
                       (current_length + len(content) < self.merge_length * 1.2):
                        buffer.append((code, content))
                        self._flush_buffer(buffer, oid)
                        oid += 1
                        buffer = []
                        current_length = 0
                        continue
                    else:
                        # Fallback: flush all
                        self._flush_buffer(buffer, oid)
                        oid += 1
                        buffer = []
                        current_length = 0
                else:
                    # Split
                    to_flush = buffer[:split_index]
                    remaining = buffer[split_index:]

                    self._flush_buffer(to_flush, oid)
                    oid += 1

                    buffer = remaining
                    current_length = sum(len(b[1]) for b in buffer)

            buffer.append((code, content))
            current_length += len(content)

        if buffer:
            self._flush_buffer(buffer, oid)

        return self.originals

    def align_paragraph(self, paragraph):
        # Compatible with using the placeholder as the separator.
        if paragraph.original[-2:] != self.separator:
            pattern = re.compile(
                r'\s*%s\s*' % self.placeholder[1].format(r'(0|[^0]\d*)'))
            paragraph.original = pattern.sub(
                self.separator, paragraph.original)
            if paragraph.translation is not None:
                paragraph.translation = pattern.sub(
                    self.separator, paragraph.translation)

        # Split originals — strip trailing separator to avoid phantom empty entry
        orig = paragraph.original
        while orig.endswith(self.separator):
            orig = orig[:-len(self.separator)]
        originals = orig.split(self.separator)

        if paragraph.translation is None:
            return list(zip(originals, [None] * len(originals)))

        # Split translations — collapse consecutive separators, strip trailing
        pattern = re.compile('(%s)+' % re.escape(self.separator))
        trans = pattern.sub(self.separator, paragraph.translation)
        while trans.endswith(self.separator):
            trans = trans[:-len(self.separator)]
        translations: list[Any] = trans.split(self.separator)

        # Fallback: if Gemini returned single newlines instead of \n\n,
        # try splitting by \n and see if the count matches exactly.
        if len(translations) < len(originals) and self.separator == '\n\n':
            alt_trans = [t for t in paragraph.translation.split('\n') if t.strip()]
            if len(alt_trans) == len(originals):
                translations = alt_trans

        # Handle count mismatches with simple sequential padding/merging.
        # IMPORTANT: originals[i] becomes a dictionary key that add_translations
        # looks up via exact string match. We MUST keep sequential order intact.
        offset = len(originals) - len(translations)
        if offset > 0:
            # Fewer translations than originals — pad with None at end
            translations += [None] * offset
        elif offset < 0:
            # More translations than originals — merge surplus into last slot
            last = len(originals) - 1
            translations = translations[:last] + [
                '\n\n'.join(translations[last:])]

        return list(zip(originals, translations))

    def prepare_translation(self, paragraphs):
        translations = []
        for paragraph in paragraphs:
            translations.extend(self.align_paragraph(paragraph))
        return dict(translations)


def get_srt_elements(path, encoding):
    elements = []
    content = open_file(path, encoding)
    for section in content.strip().split('\n\n'):
        lines = section.split('\n')
        number = lines.pop(0)
        time = lines.pop(0)
        content = '\n'.join(lines)
        elements.append(SrtElement([number, time, content]))
    return elements


def get_pgn_elements(path, encoding):
    pattern = re.compile(r'\{[^}]*[a-zA-z][^}]*\}')
    originals = pattern.findall(open_file(path, encoding))
    return [PgnElement([original, None]) for original in originals]


def get_metadata_elements(metadata):
    config = get_config()
    enable_translation = config.get(
        'ebook_metadata.metadata_translation', False)
    elements = []
    names = (
        'title', 'creator', 'publisher', 'rights', 'subject', 'contributor',
        'description')
    pattern = re.compile(r'[a-zA-Z]+')
    for key in metadata.iterkeys():
        if key not in names:
            continue
        items = getattr(metadata, key)
        for item in items:
            if pattern.search(item.content) is None:
                continue
            element = MetadataElement(
                item, page_id='content.opf', ignored=not enable_translation)
            elements.append(element)
    return elements


def get_toc_elements(nodes, elements=[], is_root=True):
    """Be aware that elements should not overlap with existing data."""
    config = get_config()
    translator_credit_enabled = config.get('translator_credit_enabled')
    translator_credit = config.get('translator_credit')
    
    for idx, node in enumerate(nodes):
        # Insert translator credit before the first TOC item
        if is_root and idx == 0 and translator_credit_enabled and translator_credit:
            node.title = f"{translator_credit}\n\n{node.title}"
        elements.append(TocElement(node, 'toc.ncx'))
        if len(node.nodes) > 0:
            get_toc_elements(node.nodes, elements, is_root=False)
    return elements


def get_page_elements(pages, spine_order=None):
    config = get_config()
    priority_rules = config.get('priority_rules')
    rule_mode = config.get('rule_mode')
    filter_scope = config.get('filter_scope')
    filter_rules = config.get('filter_rules', [])
    ignore_rules = config.get('ignore_rules', config.get('element_rules', []))
    extraction = Extraction(
        pages, priority_rules, rule_mode, filter_scope, filter_rules,
        ignore_rules, spine_order=spine_order)
    return extraction.get_elements()



class ElementHandlerChapterAware(ElementHandlerMerge):
    # Patterns to detect chapter headings (case-insensitive via re.IGNORECASE)
    # Spelled-out numbers for "chapter one" through "chapter twenty"
    SPELLED_NUMBERS = (
        'one|two|three|four|five|six|seven|eight|nine|ten|'
        'eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|'
        'unu|doi|trei|patru|cinci|șase|șapte|opt|nouă|zece|'
        'unsprezece|doisprezece|treisprezece|paisprezece|cincisprezece'
    )
    
    CHAPTER_PATTERNS = [
        # Standalone section markers
        r'^\s*(preface|introduction|prologue|epilogue|foreword|afterword)\s*$',
        r'^\s*(acknowledgements?|appendix|conclusion|bibliography|notes)\s*$',
        r'^\s*(prefață|introducere|prolog|epilog|mulțumiri|anexă|concluzie)\s*$',
        # Chapter with numbers (Arabic, Roman, or spelled-out)
        r'^\s*(chapter|capitolul|capitol)\s*(\d+|[IVXLCDM]+|' + SPELLED_NUMBERS + r')(\s|:|\.|\,|$)',
        r'^\s*(part|partea)\s*(\d+|[IVXLCDM]+|' + SPELLED_NUMBERS + r')(\s|:|\.|\,|$)',
        r'^\s*(book|cartea)\s*(\d+|[IVXLCDM]+|' + SPELLED_NUMBERS + r')(\s|:|\.|\,|$)',
        r'^\s*(section|secțiunea)\s*(\d+|[IVXLCDM]+|' + SPELLED_NUMBERS + r')(\s|:|\.|\,|$)',
        # Roman numerals only
        r'^\s*[IVXLCDM]+\s*$',
        # Arabic numerals only (1-999)
        r'^\s*\d{1,3}\s*$',
    ]
    
    def __init__(self, placeholder, separator, position):
        super().__init__(placeholder, separator, position)
        self.merge_length = 15000  # Default max chunk size for chapter aware
        self.chapter_pattern = re.compile('|'.join(self.CHAPTER_PATTERNS), re.IGNORECASE)
        self.chapters = []

    def _is_chapter_heading(self, element):
        """Check if an element is a chapter heading."""
        # Only check PageElements (which wrap actual XML elements)
        if not isinstance(element, PageElement):
            return False

        # Must be a heading tag or paragraph with specific class/style
        name = get_name(element.element)
        if name not in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div'):
            return False
            
        text = element.get_text().strip()
        if not text:
            return False
            
        # Check against patterns
        return bool(self.chapter_pattern.match(text))

    def _detect_chapters(self, elements):
        """Scan elements to find chapter boundaries."""
        chapters = []
        current_start = 0
        
        for i, element in enumerate(elements):
            if element.ignored:
                continue
                
            if self._is_chapter_heading(element):
                if i > current_start:
                    chapters.append((current_start, i))
                current_start = i
                
        # Add last chapter
        if current_start < len(elements):
            chapters.append((current_start, len(elements)))
            
        return chapters

    def prepare_original(self, elements):
        # Detect chapters first
        self.chapters = self._detect_chapters(elements)
        chapter_starts = set(start for start, end in self.chapters)
        
        oid = 0
        buffer = []
        current_length = 0
        
        # Global registry for this batch
        self.registry = {}
        global_counter = 0

        for eid, element in enumerate(elements):
            self.elements[eid] = element
            if element.ignored:
                continue
            
            # If this element is a chapter start, flush existing buffer
            # This ensures we don't merge across chapter boundaries
            if eid in chapter_starts and buffer:
                 self._flush_buffer(buffer, oid)
                 oid += 1
                 buffer = []
                 current_length = 0

            element.set_registry(self.registry)
            element.set_id_start(global_counter)

            element.set_placeholder(self.placeholder)
            element.set_position(self.position)
            element.set_target_direction(self.target_direction)
            element.set_translation_lang(self.translation_lang)
            element.set_original_color(self.original_color)
            element.set_translation_color(self.translation_color)
            if self.column_gap is not None:
                element.set_column_gap(self.column_gap)
            element.set_remove_pattern(self.remove_pattern)
            element.set_reserve_pattern(self.reserve_pattern)

            code = element.get_raw()
            content = element.get_content()
            global_counter = len(self.registry)
            content += self.separator

            if current_length + len(content) > self.merge_length:
                # Try to find a good split point
                split_index = self._find_best_split_index(buffer, current_length)

                if split_index == -1:
                    # Try extending
                    if self._is_terminator(content) and \
                       (current_length + len(content) < self.merge_length * 1.2):
                        buffer.append((code, content))
                        self._flush_buffer(buffer, oid)
                        oid += 1
                        buffer = []
                        current_length = 0
                        continue
                    else:
                        # Fallback: flush all
                        self._flush_buffer(buffer, oid)
                        oid += 1
                        buffer = []
                        current_length = 0
                else:
                    # Split
                    to_flush = buffer[:split_index]
                    remaining = buffer[split_index:]

                    self._flush_buffer(to_flush, oid)
                    oid += 1

                    buffer = remaining
                    current_length = sum(len(b[1]) for b in buffer)

            buffer.append((code, content))
            current_length += len(content)

        if buffer:
            self._flush_buffer(buffer, oid)

        return self.originals


class ElementHandlerPerFile(ElementHandlerMerge):
    """Chunking handler that groups elements by their source XHTML file.
    
    This creates one chunk per XHTML file in the original EPUB structure,
    which naturally respects the book's file-based organization (typically chapters).
    If a file exceeds the max length, it falls back to sentence-based splitting.
    """
    
    def __init__(self, placeholder, separator, position):
        super().__init__(placeholder, separator, position)
        self.merge_length = 30000  # Higher default since we're grouping by file
        self.current_page_id = None

    def prepare_original(self, elements):
        oid = 0
        buffer = []
        current_length = 0
        
        # Global registry for this batch
        self.registry = {}
        global_counter = 0
        
        # Track current page (XHTML file)
        current_page = None

        for eid, element in enumerate(elements):
            self.elements[eid] = element
            if element.ignored:
                continue
            
            # Check if we're moving to a new XHTML file
            element_page = getattr(element, 'page_id', None)
            if element_page != current_page and buffer:
                # Flush current buffer when switching files
                self._flush_buffer(buffer, oid)
                oid += 1
                buffer = []
                current_length = 0
            
            current_page = element_page
            
            element.set_registry(self.registry)
            element.set_id_start(global_counter)

            element.set_placeholder(self.placeholder)
            element.set_position(self.position)
            element.set_target_direction(self.target_direction)
            element.set_translation_lang(self.translation_lang)
            element.set_original_color(self.original_color)
            element.set_translation_color(self.translation_color)
            if self.column_gap is not None:
                element.set_column_gap(self.column_gap)
            element.set_remove_pattern(self.remove_pattern)
            element.set_reserve_pattern(self.reserve_pattern)

            code = element.get_raw()
            content = element.get_content()
            global_counter = len(self.registry)
            content += self.separator

            # Check if adding this element exceeds the max length
            if current_length + len(content) > self.merge_length:
                # Try to find a good split point within the current file
                split_index = self._find_best_split_index(buffer, current_length)

                if split_index == -1:
                    # Try extending slightly if this ends a sentence
                    if self._is_terminator(content) and \
                       (current_length + len(content) < self.merge_length * 1.2):
                        buffer.append((code, content))
                        self._flush_buffer(buffer, oid)
                        oid += 1
                        buffer = []
                        current_length = 0
                        continue
                    else:
                        # Fallback: flush all and start new chunk within same file
                        self._flush_buffer(buffer, oid)
                        oid += 1
                        buffer = []
                        current_length = 0
                else:
                    # Split at sentence boundary
                    to_flush = buffer[:split_index]
                    remaining = buffer[split_index:]

                    self._flush_buffer(to_flush, oid)
                    oid += 1

                    buffer = remaining
                    current_length = sum(len(b[1]) for b in buffer)

            buffer.append((code, content))
            current_length += len(content)

        # Flush remaining buffer
        if buffer:
            self._flush_buffer(buffer, oid)

        return self.originals


def get_element_handler(placeholder, separator, direction, chunking_method=None):
    config = get_config()
    position_alias = {'before': 'above', 'after': 'below'}
    position = config.get('translation_position', 'below')
    position = position_alias.get(position) or position
    
    # LLM engines that support advanced chunking methods
    LLM_ENGINES = ['Gemini', 'ChatGPT', 'Claude', 'ChatGPT(Azure)']
    current_engine = config.get('translate_engine', '')
    is_llm_engine = any(llm in (current_engine or '') for llm in LLM_ENGINES)
    
    # Determine chunking method
    if chunking_method is None:
        chunking_method = config.get('chunking_method', 'standard')
        # Legacy compatibility: if merge_enabled but no chunking_method set
        if chunking_method == 'standard' and config.get('merge_enabled'):
            chunking_method = 'merge'
    
    # Chapter-aware and per_file are only available for LLM engines
    # For NMT engines, fall back to 'merge'
    if chunking_method in ('chapter_aware', 'per_file') and not is_llm_engine:
        chunking_method = 'merge'
    
    # Create appropriate handler
    if chunking_method == 'per_file':
        handler = ElementHandlerPerFile(placeholder, separator, position)
    elif chunking_method == 'chapter_aware':
        handler = ElementHandlerChapterAware(placeholder, separator, position)
    elif chunking_method == 'merge' or config.get('merge_enabled'):
        handler = ElementHandlerMerge(placeholder, separator, position)
        handler.set_merge_length(config.get('merge_length'))
    else:
        handler = ElementHandler(placeholder, separator, position)

    handler.set_target_direction(direction)
    column_gap = config.get('column_gap')
    gap_type = column_gap.get('_type')
    if gap_type is not None and gap_type in column_gap.keys():
        handler.set_column_gap((gap_type, column_gap.get(gap_type)))
    handler.set_original_color(config.get('original_color'))
    handler.set_translation_color(config.get('translation_color'))
    handler.load_remove_rules(
        config.get('ignore_rules', config.get('element_rules', [])))
        
    reserve_rules = config.get('reserve_rules', [])
    if config.get('smart_html_merge', False):
        # Dynamically inject inline tags to be converted to placeholders instead of fragments
        smart_inline_tags = [
            'span', 'a', 'em', 'strong', 'b', 'i', 'u', 'small', 
            's', 'cite', 'q', 'time', 'samp', 'mark', 'data', 'del', 'ins'
        ]
        reserve_rules.extend(smart_inline_tags)
        
    handler.load_reserve_rules(reserve_rules)
    return handler

import discord
from discord import app_commands
from discord.ext import tasks
import json
import os
import re
import random
import asyncio
import atexit
import hashlib
import math
from collections import defaultdict, deque, OrderedDict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set, Any, Union
from enum import Enum
import emoji
import numpy as np

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, defaultdict):
            return dict(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.float32):
            return float(obj)
        if isinstance(obj, np.float64):
            return float(obj)
        if isinstance(obj, np.int32):
            return int(obj)
        if isinstance(obj, np.int64):
            return int(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)

class Language(Enum):
    RUSSIAN = "ru"
    ENGLISH = "en"
    MIXED = "mixed"
    UNKNOWN = "unknown"

class ContentType(Enum):
    TEXT = "text"
    URL = "url"
    EMOJI = "emoji"
    MENTION = "mention"
    COMMAND = "command"
    IMAGE = "image"

class FastCPUClassifier:
    """Ультра-быстрая нейросеть для классификации на CPU"""
    
    def __init__(self, input_size=128, hidden_size=64, output_size=12):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        self.W1 = np.random.randn(input_size, hidden_size).astype(np.float32) * 0.01
        self.b1 = np.zeros((1, hidden_size), dtype=np.float32)
        self.W2 = np.random.randn(hidden_size, output_size).astype(np.float32) * 0.01
        self.b2 = np.zeros((1, output_size), dtype=np.float32)
        
        self.intent_map = {
            0: "greeting",
            1: "question",
            2: "statement",
            3: "command",
            4: "joke",
            5: "complaint",
            6: "thanks",
            7: "help",
            8: "story",
            9: "opinion",
            10: "fact",
            11: "other"
        }
        
        self.vector_cache = {}
    
    def text_to_vector(self, text: str) -> np.ndarray:
        text_hash = hash(text[:50])
        if text_hash in self.vector_cache:
            return self.vector_cache[text_hash]
        
        vector = np.zeros(self.input_size, dtype=np.float32)
        text = text.lower()[:100]
        
        vector[0] = min(len(text) / 100, 1.0)
        
        vector[1] = 1.0 if any(c in text for c in '?!') else 0.0
        vector[2] = text.count('?') / 5.0
        vector[3] = text.count('!') / 5.0
        
        ru_chars = sum(1 for c in text if 'а' <= c <= 'я' or c in 'ё')
        en_chars = sum(1 for c in text if 'a' <= c <= 'z')
        total = max(ru_chars + en_chars, 1)
        vector[4] = ru_chars / total
        vector[5] = en_chars / total
        
        for i in range(len(text) - 2):
            trigram = text[i:i+3]
            trigram_hash = hash(trigram) % (self.input_size - 10)
            vector[10 + trigram_hash] += 1.0
        
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        self.vector_cache[text_hash] = vector
        if len(self.vector_cache) > 10000:
            keys = list(self.vector_cache.keys())[:5000]
            for k in keys:
                del self.vector_cache[k]
        
        return vector
    
    def relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)
    
    def softmax(self, x: np.ndarray) -> np.ndarray:
        exp_x = np.exp(x - np.max(x))
        return exp_x / np.sum(exp_x, axis=1, keepdims=True)
    
    def predict(self, text: str) -> Tuple[str, np.ndarray]:
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['привет', 'здравствуй', 'хай', 'hello', 'hi', 'hey']):
            return "greeting", np.array([0.9] + [0.01]*11, dtype=np.float32)
        
        if '?' in text_lower:
            return "question", np.array([0.1, 0.8] + [0.01]*10, dtype=np.float32)
        
        if any(word in text_lower for word in ['спасибо', 'thanks', 'thank you', 'благодарю']):
            return "thanks", np.array([0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.7] + [0.01]*5, dtype=np.float32)
        
        X = self.text_to_vector(text).reshape(1, -1)
        
        z1 = np.dot(X, self.W1) + self.b1
        a1 = self.relu(z1)
        z2 = np.dot(a1, self.W2) + self.b2
        probs = self.softmax(z2)
        
        intent_idx = np.argmax(probs[0])
        confidence = probs[0][intent_idx]
        
        if confidence < 0.3:
            if len(text) < 10:
                return "greeting", probs[0]
            elif '?' in text:
                return "question", probs[0]
            else:
                return "statement", probs[0]
        
        return self.intent_map[intent_idx], probs[0]
    
    def train_online(self, text: str, true_intent: str, learning_rate: float = 0.01):
        X = self.text_to_vector(text).reshape(1, -1)
        
        z1 = np.dot(X, self.W1) + self.b1
        a1 = self.relu(z1)
        z2 = np.dot(a1, self.W2) + self.b2
        probs = self.softmax(z2)
        
        y_true = np.zeros((1, self.output_size), dtype=np.float32)
        intent_idx = list(self.intent_map.keys())[list(self.intent_map.values()).index(true_intent)]
        y_true[0, intent_idx] = 1
        
        dz2 = probs - y_true
        dW2 = np.dot(a1.T, dz2)
        db2 = np.sum(dz2, axis=0, keepdims=True)
        
        dz1 = np.dot(dz2, self.W2.T) * (a1 > 0)
        dW1 = np.dot(X.T, dz1)
        db1 = np.sum(dz1, axis=0, keepdims=True)
        
        self.W2 -= learning_rate * dW2
        self.b2 -= learning_rate * db2
        self.W1 -= learning_rate * dW1
        self.b1 -= learning_rate * db1

class KnowledgeNode:
    def __init__(self, name: str, node_type: str = "concept"):
        self.id = hashlib.md5(name.encode()).hexdigest()[:12]
        self.name = name
        self.node_type = node_type
        self.weight = 1.0
        self.last_accessed = datetime.now().isoformat()
        self.attributes = {}
        self.relations = defaultdict(float)
        
    def add_relation(self, other_node_id: str, relation_type: str, strength: float = 1.0):
        key = f"{other_node_id}:{relation_type}"
        current = self.relations.get(key, 0)
        self.relations[key] = min(1.0, current + strength * 0.1)
        self.last_accessed = datetime.now().isoformat()
        
    def get_related(self, relation_type: str = None, min_strength: float = 0.3):
        related = []
        for key, strength in self.relations.items():
            if strength >= min_strength:
                if relation_type is None or key.endswith(f":{relation_type}"):
                    node_id = key.split(":")[0]
                    related.append((node_id, strength))
        
        # Сортировка по силе связи
        related.sort(key=lambda x: x[1], reverse=True)
        return related

class KnowledgeGraph:
    def __init__(self):
        self.nodes = {}
        self.node_by_name = {}
        self.relation_types = {
            "is_a": 1.0,
            "has_property": 0.8,
            "part_of": 0.7,
            "can": 0.6,
            "located_in": 0.5,
            "similar_to": 0.4,
            "opposite_of": 0.3,
            "causes": 0.2,
            "used_for": 0.9,
            "created_by": 0.8,
        }
        
        self.load_base_knowledge()
    
    def load_base_knowledge(self):
        base_facts = [
            ("кошка", "is_a", "животное"),
            ("собака", "is_a", "животное"),
            ("птица", "is_a", "животное"),
            ("рыба", "is_a", "животное"),
            ("кошка", "has_property", "мягкая"),
            ("собака", "has_property", "верная"),
            ("птица", "can", "летать"),
            ("рыба", "can", "плавать"),
            ("человек", "is_a", "животное"),
            ("человек", "can", "говорить"),
            ("человек", "can", "думать"),
            ("человек", "can", "работать"),
            ("солнце", "has_property", "горячее"),
            ("луна", "has_property", "холодная"),
            ("вода", "has_property", "мокрая"),
            ("огонь", "has_property", "горячий"),
            ("дерево", "has_property", "высокое"),
            ("день", "opposite_of", "ночь"),
            ("утро", "part_of", "день"),
            ("вечер", "part_of", "день"),
            ("радость", "opposite_of", "грусть"),
            ("любовь", "opposite_of", "ненависть"),
            ("смех", "has_property", "веселый"),
            ("компьютер", "used_for", "работать"),
            ("телефон", "used_for", "звонить"),
            ("интернет", "used_for", "общаться"),
            ("яблоко", "has_property", "вкусное"),
            ("хлеб", "has_property", "свежий"),
            ("вода", "has_property", "полезная"),
        ]
        
        for subj, rel, obj in base_facts:
            self.add_fact(subj, rel, obj)
    
    def get_or_create_node(self, name: str, node_type: str = "concept") -> str:
        if name in self.node_by_name:
            node_id = self.node_by_name[name]
            self.nodes[node_id].last_accessed = datetime.now().isoformat()
            return node_id
        
        node = KnowledgeNode(name, node_type)
        self.nodes[node.id] = node
        self.node_by_name[name] = node.id
        return node.id
    
    def add_fact(self, subject: str, relation: str, obj: str, strength: float = None):
        if strength is None:
            strength = self.relation_types.get(relation, 0.5)
        
        subj_id = self.get_or_create_node(subject)
        obj_id = self.get_or_create_node(obj)
        
        self.nodes[subj_id].add_relation(obj_id, relation, strength)
        
        reverse_relations = {
            "is_a": "includes",
            "part_of": "contains",
            "opposite_of": "opposite_of",
        }
        
        if relation in reverse_relations:
            rev_relation = reverse_relations[relation]
            self.nodes[obj_id].add_relation(subj_id, rev_relation, strength * 0.8)
    
    def infer(self, subject: str, relation: str, max_depth: int = 2) -> List[Tuple[str, float]]:
        if subject not in self.node_by_name:
            return []
        
        start_id = self.node_by_name[subject]
        results = []
        visited = set()
        
        def dfs(current_id: str, depth: int, path_strength: float):
            if depth > max_depth:
                return
            
            visited.add(current_id)
            node = self.nodes[current_id]
            
            for key, strength in node.relations.items():
                other_id, rel_type = key.split(":")
                if rel_type == relation:
                    if other_id not in visited:
                        final_strength = path_strength * strength
                        results.append((self.nodes[other_id].name, final_strength))
                
                if depth < max_depth:
                    dfs(other_id, depth + 1, path_strength * strength * 0.7)
        
        dfs(start_id, 0, 1.0)
        
        result_dict = defaultdict(float)
        for name, strength in results:
            result_dict[name] = max(result_dict[name], strength)
        
        sorted_results = sorted(result_dict.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:10]
    
    def find_connection(self, concept1: str, concept2: str, max_depth: int = 3) -> Optional[List[str]]:
        if concept1 not in self.node_by_name or concept2 not in self.node_by_name:
            return None
        
        start_id = self.node_by_name[concept1]
        target_id = self.node_by_name[concept2]
        
        queue = deque([(start_id, [], 1.0)])
        visited = {start_id}
        
        while queue:
            current_id, path, total_strength = queue.popleft()
            
            if current_id == target_id:
                return path
            
            if len(path) >= max_depth:
                continue
            
            current_node = self.nodes[current_id]
            
            for key, strength in current_node.relations.items():
                other_id, rel_type = key.split(":")
                
                if other_id not in visited:
                    visited.add(other_id)
                    new_path = path + [(self.nodes[other_id].name, rel_type, strength)]
                    new_strength = total_strength * strength
                    
                    if new_strength > 0.1:
                        queue.append((other_id, new_path, new_strength))
        
        return None

class WorkingMemory:
    def __init__(self, capacity: int = 10):
        self.capacity = capacity
        self.slots = OrderedDict()
        self.attention_weights = {}
        self.current_focus = None
    
    def update(self, concept: str, relevance: float = 1.0):
        if len(concept) < 3 or concept in ['это', 'тот', 'такой', 'какой']:
            return
        
        now = datetime.now().isoformat()
        
        if concept in self.slots:
            old_data = self.slots[concept]
            new_relevance = old_data['relevance'] * 0.9 + relevance * 0.1
            self.slots[concept] = {
                'relevance': min(1.0, new_relevance),
                'timestamp': now
            }
            
            self.slots.move_to_end(concept)
        else:
            if len(self.slots) >= self.capacity:
                least_relevant = min(self.slots.items(), key=lambda x: x[1]['relevance'])
                del self.slots[least_relevant[0]]
            
            self.slots[concept] = {
                'relevance': relevance,
                'timestamp': now
            }
        
        self.update_focus()
    
    def update_focus(self):
        if not self.slots:
            self.current_focus = None
            return
        
        best_concept = None
        best_score = -1
        
        for concept, data in self.slots.items():
            try:
                timestamp = datetime.fromisoformat(data['timestamp'])
                freshness = 1.0 / (1.0 + (datetime.now() - timestamp).seconds / 60.0)
            except:
                freshness = 0.5
            
            score = data['relevance'] * freshness
            
            if score > best_score:
                best_score = score
                best_concept = concept
        
        self.current_focus = best_concept
    
    def get_context(self, count: int = 3) -> List[str]:
        filtered_concepts = [
            (concept, data) for concept, data in self.slots.items() 
            if len(concept) > 2
        ]
        
        if not filtered_concepts:
            return []
        
        sorted_concepts = sorted(
            filtered_concepts,
            key=lambda x: x[1]['relevance'],
            reverse=True
        )[:count]
        
        return [concept for concept, _ in sorted_concepts]
    
    def get_focus_score(self, concept: str) -> float:
        if concept not in self.slots:
            return 0.0
        
        data = self.slots[concept]
        try:
            timestamp = datetime.fromisoformat(data['timestamp'])
            freshness = 1.0 / (1.0 + (datetime.now() - timestamp).seconds / 60.0)
        except:
            freshness = 0.5
        
        return data['relevance'] * freshness
    
    def decay(self, decay_rate: float = 0.95):
        for concept in list(self.slots.keys()):
            self.slots[concept]['relevance'] *= decay_rate
            
            if self.slots[concept]['relevance'] < 0.05:
                del self.slots[concept]
        
        self.update_focus()

class FastSemanticSearch:
    def __init__(self):
        self.documents = []
        self.inverted_index = defaultdict(set)
        self.embedding_cache = {}
        self.next_id = 0
    
    def simple_embedding(self, text: str) -> np.ndarray:
        text_hash = hash(text[:100])
        if text_hash in self.embedding_cache:
            return self.embedding_cache[text_hash]
        
        vector = np.zeros(128, dtype=np.float32)
        words = text.lower().split()
        
        for word in words[:20]:
            for i in range(len(word) - 2):
                trigram = word[i:i+3]
                idx = hash(trigram) % 128
                vector[idx] += 1.0
        
        vector[0] = min(len(text) / 200.0, 1.0)
        
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        self.embedding_cache[text_hash] = vector
        if len(self.embedding_cache) > 5000:
            keys = list(self.embedding_cache.keys())[:2500]
            for k in keys:
                del self.embedding_cache[k]
        
        return vector
    
    def add_document(self, text: str, tags: List[str] = None):
        if len(text.split()) < 3:
            return
        
        doc_id = self.next_id
        self.next_id += 1
        
        embedding = self.simple_embedding(text)
        tags_set = set(tags or [])
        
        document = {
            'id': doc_id,
            'text': text[:500],
            'embedding': embedding.tolist(),
            'tags': tags_set,
            'added_at': datetime.now().isoformat()
        }
        
        self.documents.append(document)
        
        words = text.lower().split()
        for word in set(words):
            if len(word) >= 3:
                self.inverted_index[word].add(doc_id)
        
        if len(self.documents) > 10000:
            self.documents.sort(key=lambda x: x['added_at'])
            removed = self.documents[:1000]
            self.documents = self.documents[1000:]
            
            for doc in removed:
                words = doc['text'].lower().split()
                for word in set(words):
                    if word in self.inverted_index:
                        self.inverted_index[word].discard(doc['id'])
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def search(self, query: str, k: int = 5, use_index: bool = True) -> List[Tuple[float, str]]:
        if len(query.split()) < 2:
            return []
        
        query_embedding = self.simple_embedding(query)
        query_words = set(query.lower().split())
        
        candidate_ids = set()
        
        if use_index and len(self.documents) > 100:
            for word in query_words:
                if word in self.inverted_index:
                    candidate_ids.update(self.inverted_index[word])
            
            if len(candidate_ids) < k * 2:
                candidate_ids.update(random.sample(
                    range(len(self.documents)), 
                    min(100, len(self.documents))
                ))
        else:
            candidate_ids = set(range(len(self.documents)))
        
        results = []
        for doc_id in candidate_ids:
            if doc_id >= len(self.documents):
                continue
            
            doc = self.documents[doc_id]
            similarity = self.cosine_similarity(
                query_embedding, 
                np.array(doc['embedding'], dtype=np.float32)
            )
            
            tag_bonus = 0.0
            if doc['tags']:
                matching_tags = len(doc['tags'].intersection(query_words))
                tag_bonus = matching_tags * 0.1
            
            final_score = similarity + tag_bonus
            if final_score > 0.3:
                if len(doc['text'].split()) > 2:
                    results.append((final_score, doc['text']))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:k]

class RuleBasedReasoner:
    def __init__(self):
        self.rules = [
            ("is_a(X, Y) AND has_property(Y, Z)", "has_property(X, Z)", 0.8),
            ("is_a(X, Y) AND can(Y, Z)", "possibly_can(X, Z)", 0.6),
            ("opposite_of(X, Y) AND has_property(X, Z)", "has_property(Y, opposite_of(Z))", 0.7),
            ("part_of(X, Y) AND located_in(Y, Z)", "located_in(X, Z)", 0.9),
            ("similar_to(X, Y) AND likes(Y, Z)", "might_like(X, Z)", 0.5),
            ("causes(X, Y) AND causes(Y, Z)", "indirectly_causes(X, Z)", 0.4),
            ("used_for(X, Y) AND part_of(Y, Z)", "used_for(X, Z)", 0.3),
        ]
        
        self.pattern_cache = {}
    
    def apply_rules(self, facts: List[str], knowledge_graph: KnowledgeGraph) -> List[str]:
        new_facts = []
        
        for rule_pattern, conclusion_pattern, confidence in self.rules:
            for fact in facts:
                inference = self.try_apply_rule(fact, rule_pattern, conclusion_pattern, knowledge_graph)
                if inference and random.random() < confidence:
                    new_facts.append(inference)
        
        return new_facts[:10]
    
    def try_apply_rule(self, fact: str, rule_pattern: str, conclusion_pattern: str, 
                      knowledge_graph: KnowledgeGraph) -> Optional[str]:
        if "is_a" in rule_pattern and "is_a" in fact:
            parts = fact.split()
            if len(parts) >= 3 and parts[1] == "is_a":
                X = parts[0]
                Y = parts[2]
                
                properties = knowledge_graph.infer(Y, "has_property")
                if properties:
                    property_name, strength = random.choice(properties[:3])
                    if strength > 0.5:
                        return f"{X} has_property {property_name}"
        
        return None

class PersonalityModule:
    """Модуль адаптивной личности ИИ"""
    
    def __init__(self):
        self.traits = {
            "formality": 0.5,
            "humor": 0.4,
            "curiosity": 0.7,
            "empathy": 0.6,
            "enthusiasm": 0.5,
            "sarcasm": 0.2,
            "creativity": 0.3,
        }
        
        self.user_adaptations = defaultdict(dict)
        self.mood = 0.5
        self.energy = 0.8
        
        self.response_templates = {
            "formal": [
                "Безусловно, {response}",
                "Согласно имеющейся информации, {response}",
                "Могу сообщить, что {response}",
            ],
            "casual": [
                "Да, {response}",
                "Ну, {response}",
                "Вообще, {response}",
            ],
            "humorous": [
                "Ахаха, {response} 😂",
                "Ну ты даёшь! {response}",
                "Ого, {response} 🤣",
            ],
            "curious": [
                "Интересно! {response} Кстати, а что ты сам думаешь?",
                "Хм, {response} А почему ты спрашиваешь?",
                "{response} Кстати, это напомнило мне кое-что...",
            ],
            "empathetic": [
                "Понимаю тебя. {response}",
                "Чувствую, что {response} Надеюсь, это поможет.",
                "{response} Я с тобой.",
            ]
        }
    
    def adapt_to_user(self, user_id: str, message: str, user_mood: float = 0.0):
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['шутк', 'прикол', 'смешн', 'хаха', 'lol', '😂', '🤣']):
            self.user_adaptations[user_id]["humor"] = min(
                self.user_adaptations[user_id].get("humor", 0.5) + 0.1,
                1.0
            )
        
        if '?' in message:
            self.user_adaptations[user_id]["curiosity"] = min(
                self.user_adaptations[user_id].get("curiosity", 0.5) + 0.05,
                1.0
            )
        
        if any(word in message_lower for word in ['груст', 'печал', 'плох', 'bad', 'sad', '😢', '😔']):
            self.user_adaptations[user_id]["empathy"] = min(
                self.user_adaptations[user_id].get("empathy", 0.5) + 0.15,
                1.0
            )
            self.mood -= 0.1
        
        if any(word in message_lower for word in ['рад', 'весел', 'хорош', 'good', 'happy', '😊', '😄']):
            self.mood += 0.1
        
        self.energy *= 0.999
        if self.energy < 0.3:
            self.energy = 0.3
    
    def get_user_trait(self, user_id: str, trait: str) -> float:
        base_trait = self.traits.get(trait, 0.5)
        user_trait = self.user_adaptations[user_id].get(trait, base_trait)
        
        if trait == "enthusiasm":
            user_trait *= self.energy
        
        if trait == "humor":
            user_trait *= (self.mood * 0.5 + 0.5)
        
        return max(0.0, min(1.0, user_trait))
    
    def style_response(self, response: str, user_id: str = None) -> str:
        if not response:
            return response
        
        traits_to_check = ["humor", "formality", "curiosity", "empathy"]
        trait_values = []
        
        for trait in traits_to_check:
            if user_id:
                value = self.get_user_trait(user_id, trait)
            else:
                value = self.traits[trait]
            trait_values.append((trait, value))
        
        trait_values.sort(key=lambda x: x[1], reverse=True)
        dominant_trait, dominant_value = trait_values[0]
        
        if dominant_value > 0.7:
            template_type = dominant_trait
            if template_type in self.response_templates:
                template = random.choice(self.response_templates[template_type])
                
                if len(response) > 150:
                    response = response[:147] + "..."
                
                try:
                    return template.format(response=response)
                except:
                    pass
        
        if self.traits["humor"] > 0.6 and random.random() < 0.2:
            emojis = ["😊", "😂", "😎", "🤔", "😉", "😄"]
            response += f" {random.choice(emojis)}"
        
        if self.traits["formality"] < 0.3:
            response = response.replace("Вы", "ты").replace("Вам", "тебе")
        
        return response

class AdvancedAI:
    def __init__(self, max_memory_size: int = 10000):
        self.classifier = FastCPUClassifier()
        self.knowledge_graph = KnowledgeGraph()
        self.working_memory = WorkingMemory(capacity=15)
        self.semantic_search = FastSemanticSearch()
        self.reasoner = RuleBasedReasoner()
        self.personality = PersonalityModule()
        
        self.knowledge_base = defaultdict(dict)
        self.user_profiles = {}
        self.conversation_history = []
        self.response_variants = defaultdict(list)
        self.url_database = defaultdict(dict)
        self.emoji_database = defaultdict(dict)
        
        self.max_memory_size = max_memory_size
        self.learning_rate = 0.1
        self.decay_factor = 0.995
        self.min_word_length = 2
        
        self.stop_words = {
            "и", "в", "на", "с", "по", "для", "не", "что", "это", "как",
            "но", "а", "или", "у", "о", "от", "то", "из", "за", "к",
            "же", "вот", "бы", "ли", "ну", "да", "нет", "так", "вон",
            "он", "она", "оно", "они", "мы", "вы", "я", "ты", "мой",
            "твой", "наш", "ваш", "его", "её", "их", "мне", "тебе",
            "ему", "ей", "нам", "вам", "меня", "тебя", "него", "неё",
            "них", "нас", "вас", "мной", "тобой", "ним", "ней", "ними",
            "этот", "эта", "это", "эти", "тот", "та", "то", "те",
            "такой", "такая", "такое", "такие", "какой", "какая",
            "какое", "какие", "который", "которая", "которое", "которые",
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "as", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does",
            "did", "will", "would", "can", "could", "should", "may",
            "might", "must", "shall", "so", "too", "very", "just", "now",
            "then", "here", "there", "when", "where", "why", "how",
            "ах", "ох", "эй", "ого", "ух", "эх", "ну", "вот", "так",
            "же", "ли", "бы", "как", "что", "да", "нет", "ага", "угу",
            "кто", "что", "где", "куда", "когда", "почему", "зачем",
        }
        
        self.response_cache = OrderedDict()
        self.similarity_cache = {}
        self.intent_cache = {}
        
        self.stats = {
            "total_learned": 0,
            "total_responses": 0,
            "avg_response_time": 0,
            "active_users": set(),
            "last_activity": datetime.now().isoformat()
        }
        
        self.load_config()
        
        self.pre_train()
    
    def load_config(self):
        try:
            if plugin_file_exists("config.json"):
                config_content = read_plugin_file("config.json")
                config = json.loads(config_content)
                
                self.learning_rate = config.get("learning_rate", 0.1)
                self.decay_factor = config.get("decay_factor", 0.995)
                self.min_word_length = config.get("min_word_length", 2)
                
                if "personality_traits" in config:
                    for trait, value in config["personality_traits"].items():
                        if trait in self.personality.traits:
                            self.personality.traits[trait] = value
                
        except Exception as e:
            print(f"❌ AI: Ошибка загрузки конфига: {e}")
    
    def pre_train(self):
        basic_qna = [
            ("привет", "Привет! Как дела?"),
            ("здравствуй", "Здравствуй! Как настроение?"),
            ("хай", "Хай! Что нового?"),
            ("hello", "Hello! How are you?"),
            ("hi", "Hi! What's up?"),
            ("hey", "Hey! How's it going?"),
            
            ("как дела", "Отлично, учусь новому! А у тебя?"),
            ("how are you", "I'm good, thanks! Learning new things every day."),
            ("what's up", "Not much, just chatting with people like you!"),
            
            ("что делаешь", "Общаюсь с людьми и учусь на разговорах!"),
            ("what are you doing", "I'm learning from conversations!"),
            
            ("кто ты", "Я ИИ, который обучается в реальном времени из наших диалогов!"),
            ("what are you", "I'm an AI that learns in real time from our conversations!"),
            
            ("спасибо", "Всегда пожалуйста! Рад помочь!"),
            ("thanks", "You're welcome! 😊"),
            ("thank you", "My pleasure!"),
            
            ("помощь", "Я могу: отвечать на вопросы, учиться из разговоров, запоминать контекст!"),
            ("help", "I can: answer questions, learn from conversations, remember context!"),
            
            ("что умеешь", "Я учусь из разговоров и могу отвечать на вопросы! Также запоминаю контекст."),
            ("what can you do", "I learn from conversations and can answer questions! I also remember context."),
            
            ("пока", "Пока! Было приятно пообщаться!"),
            ("до свидания", "До свидания! Возвращайся еще!"),
            ("bye", "Bye! Nice talking to you!"),
            ("goodbye", "Goodbye! Come back soon!"),
        ]
        
        for question, answer in basic_qna:
            self.learn_from_message("system", question, answer)
    
    def learn_from_message(self, user_id: str, message: str, response: str = None):
        start_time = datetime.now()
        
        words = self.extract_words(message)
        
        if not words and not response:
            return
        
        self.update_user_profile(user_id, message, words)
        
        if response:
            intent = self.guess_intent_from_response(response)
            if intent:
                self.classifier.train_online(message, intent, self.learning_rate)
        
        if words and len(words) > 2:
            self.semantic_search.add_document(message, words)
            nouns = [w for w in words if len(w) > 3]
            for i in range(len(nouns) - 1):
                self.knowledge_graph.add_fact(nouns[i], "related_to", nouns[i+1], 0.3)
        
        if response and words:
            question_key = ' '.join(sorted(set(words)))
            
            if question_key not in self.response_variants:
                self.response_variants[question_key] = []
            
            existing = False
            for i, (resp, weight, users) in enumerate(self.response_variants[question_key]):
                if resp[:50] == response[:50]:
                    existing = True
                    self.response_variants[question_key][i] = (
                        resp, 
                        weight * 0.9 + 0.1, 
                        users.union({user_id})
                    )
                    break
            
            if not existing:
                self.response_variants[question_key].append(
                    (response[:200], 1.0, {user_id})
                )
                
                if len(self.response_variants[question_key]) > 5:
                    self.response_variants[question_key].sort(key=lambda x: x[1])
                    self.response_variants[question_key].pop(0)
        
        self.stats["total_learned"] += 1
        self.stats["active_users"].add(user_id)
        self.stats["last_activity"] = datetime.now().isoformat()
        
        for word in words[:5]:
            if len(word) > 2:
                self.working_memory.update(word, 1.0)
    
    def guess_intent_from_response(self, response: str) -> Optional[str]:
        response_lower = response.lower()
        
        if any(word in response_lower for word in ['привет', 'здравствуй', 'hello', 'hi', 'hey']):
            return "greeting"
        
        if '?' in response:
            return "question"
        
        if any(word in response_lower for word in ['спасибо', 'благодарю', 'thanks', 'thank you']):
            return "thanks"
        
        if any(word in response_lower for word in ['шутк', 'смех', 'хаха', 'lol', '😂']):
            return "joke"
        
        if any(word in response_lower for word in ['помощь', 'help', 'подсказ']):
            return "help"
        
        return "statement"
    
    def extract_words(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r'[^\w\sа-яА-ЯёЁa-zA-Z]', ' ', text)
        words = text.split()
        filtered = []
        for word in words:
            if len(word) < self.min_word_length:
                continue
            
            if word in self.stop_words:
                continue
            
            if word.isdigit():
                continue
            
            if len(word) > 20:
                continue
            
            filtered.append(word)
        
        return filtered
    
    def update_user_profile(self, user_id: str, message: str, words: List[str]):
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'message_count': 0,
                'vocabulary': set(),
                'last_message': datetime.now().isoformat(),
                'avg_length': 0,
                'preferred_topics': defaultdict(int)
            }
        
        profile = self.user_profiles[user_id]
        profile['message_count'] += 1
        profile['last_message'] = datetime.now().isoformat()
        profile['vocabulary'].update(words)
        total_len = profile.get('total_length', 0) + len(message)
        profile['total_length'] = total_len
        profile['avg_length'] = total_len / profile['message_count']
        for word in words[:3]:
            if len(word) > 3:
                profile['preferred_topics'][word] += 1
    
    def generate_response(self, message: str, user_id: str = None) -> str:
        start_time = datetime.now()
        cache_key = f"{user_id}:{hash(message[:50])}"
        if cache_key in self.response_cache:
            return self.response_cache[cache_key]
        intent, probs = self.classifier.predict(message)

        if user_id:
            self.personality.adapt_to_user(user_id, message)
        words = self.extract_words(message)

        for word in words[:3]:
            if len(word) > 2:
                self.working_memory.update(word, 1.0)

        exact_response = self.find_exact_response(message, user_id)
        if exact_response:
            final_response = self.personality.style_response(exact_response, user_id)
            self.cache_response(cache_key, final_response)
            self.update_stats(start_time)
            return final_response
        
        basic_response = self.get_basic_response(message, intent)
        if basic_response:
            final_response = self.personality.style_response(basic_response, user_id)
            self.cache_response(cache_key, final_response)
            self.update_stats(start_time)
            return final_response
        
        semantic_results = self.semantic_search.search(message, k=3)
        if semantic_results:
            best_score, best_text = semantic_results[0]
            if best_score > 0.7 and len(best_text.split()) > 3:
                response = self.transform_to_response(best_text, message)
                if response and len(response.split()) > 2:
                    final_response = self.personality.style_response(response, user_id)
                    self.cache_response(cache_key, final_response)
                    self.update_stats(start_time)
                    return final_response
        
        nouns = [w for w in words if len(w) > 3]
        if len(nouns) >= 1:
            logic_response = self.try_logical_reasoning(nouns, message)
            if logic_response:
                final_response = self.personality.style_response(logic_response, user_id)
                self.cache_response(cache_key, final_response)
                self.update_stats(start_time)
                return logic_response
        
        context_response = self.generate_from_context_improved(message, user_id, intent, words)
        if context_response:
            final_response = self.personality.style_response(context_response, user_id)
            self.cache_response(cache_key, final_response)
            self.update_stats(start_time)
            return final_response
        
        fallback = self.get_fallback_response_improved(intent, message, user_id)
        final_response = self.personality.style_response(fallback, user_id)
        
        self.cache_response(cache_key, final_response)
        self.update_stats(start_time)
        return final_response
    
    def get_basic_response(self, message: str, intent: str) -> Optional[str]:
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['привет', 'здравствуй', 'хай', 'hello', 'hi', 'hey']):
            responses = [
                "Привет! Рад тебя видеть!",
                "Здравствуй! Как настроение?",
                "Привет! Что нового?",
                "Приветствую! Как дела?",
                "Хай! Как сам?",
                "Hello! How are you?",
                "Hi there! What's up?",
                "Hey! Nice to see you!",
            ]
            return random.choice(responses)
        
        if any(word in message_lower for word in ['как дела', 'how are', 'как ты', 'как жизнь']):
            responses = [
                "Отлично, учусь новому! А у тебя?",
                "Хорошо, спасибо! Как сам?",
                "Прекрасно! Общаюсь с интересными людьми.",
                "Нормально, работаю. А ты как?",
                "I'm great! Learning new things every day.",
                "Good, thanks! How about you?",
                "Not bad! What about you?",
            ]
            return random.choice(responses)
        
        if any(word in message_lower for word in ['кто ты', 'что ты', 'ты кто', 'ты что', 'what are you']):
            responses = [
                "Я ИИ, который учится из наших разговоров!",
                "Я умный алгоритм, обучающийся в реальном времени.",
                "I'm an AI that learns from conversations.",
                "Я бот с искусственным интеллектом, становлюсь умнее с каждым сообщением!",
                "Я нейросеть, которая учится у людей.",
                "I'm a learning AI. The more we chat, the smarter I get!",
            ]
            return random.choice(responses)
        
        if any(word in message_lower for word in ['спасибо', 'thanks', 'thank you', 'благодарю']):
            responses = [
                "Всегда пожалуйста!",
                "Рад был помочь!",
                "Не за что! Обращайся!",
                "You're welcome!",
                "My pleasure!",
                "No problem!",
                "Anytime!",
            ]
            return random.choice(responses)
        
        if any(word in message_lower for word in ['пока', 'до свидания', 'bye', 'goodbye']):
            responses = [
                "Пока! Было приятно пообщаться!",
                "До свидания! Возвращайся еще!",
                "Bye! Nice talking to you!",
                "Goodbye! Come back soon!",
                "See you later!",
                "Take care!",
            ]
            return random.choice(responses)
        
        if '?' in message:
            if 'почему' in message_lower:
                responses = [
                    "Это интересный вопрос! Дай мне подумать...",
                    "На это есть несколько причин...",
                    "Сложно ответить коротко, но попробую объяснить.",
                    "That's a good question. Let me think about it...",
                ]
                return random.choice(responses)
            elif 'как' in message_lower:
                responses = [
                    "Сложно объяснить кратко, но попробую...",
                    "Это зависит от многих факторов...",
                    "Давай разберем по шагам...",
                    "Let me explain how it works...",
                ]
                return random.choice(responses)
            elif 'что' in message_lower:
                responses = [
                    "На этот вопрос может быть несколько ответов...",
                    "Это хороший вопрос! Дай мне секунду...",
                    "Что именно тебя интересует?",
                    "That depends on what you mean...",
                ]
                return random.choice(responses)
            elif 'где' in message_lower or 'куда' in message_lower:
                responses = [
                    "Это зависит от многих факторов...",
                    "Нужно больше информации, чтобы ответить точно.",
                    "Где именно ты ищешь?",
                    "It depends on the location...",
                ]
                return random.choice(responses)
            elif 'когда' in message_lower:
                responses = [
                    "Трудно сказать точно...",
                    "Это зависит от обстоятельств.",
                    "Нужно уточнить детали.",
                    "It's hard to say exactly when...",
                ]
                return random.choice(responses)
            
            responses = [
                "Интересный вопрос! Дайте мне секунду подумать...",
                "Хм, хороший вопрос. Дай-ка подумать...",
                "Сложный вопрос! Что ты сам об этом думаешь?",
                "I need to think about that...",
                "Let me think for a moment...",
                "That's a tough one. What do you think?",
            ]
            return random.choice(responses)
        
        if intent == "statement" and len(message.split()) > 3:
            positive_words = ['хорош', 'отличн', 'прекрасн', 'замечательн', 'класс', 'крут']
            negative_words = ['плох', 'ужасн', 'скучн', 'грустн', 'печальн']
            
            if any(word in message_lower for word in positive_words):
                responses = [
                    "Согласен! Это действительно здорово!",
                    "Верно подмечено!",
                    "Да, это прекрасно!",
                    "Absolutely! That's great!",
                ]
                return random.choice(responses)
            elif any(word in message_lower for word in negative_words):
                responses = [
                    "Понимаю тебя...",
                    "Это печально...",
                    "Сочувствую...",
                    "I understand how you feel...",
                ]
                return random.choice(responses)
        
        return None
    
    def find_exact_response(self, message: str, user_id: str = None) -> Optional[str]:
        words = self.extract_words(message)
        if not words:
            return None
        
        question_key = ' '.join(sorted(set(words)))
        
        if question_key in self.response_variants and self.response_variants[question_key]:
            variants = self.response_variants[question_key]
            
            total_weight = sum(weight for _, weight, _ in variants)
            if total_weight > 0:
                rand_val = random.random() * total_weight
                cumulative = 0
                
                for response, weight, users in variants:
                    cumulative += weight
                    
                    if user_id and user_id in users:
                        cumulative += weight * 0.5
                    
                    if rand_val <= cumulative:
                        return response
            
            best_variant = max(variants, key=lambda x: x[1])
            return best_variant[0]
        
        return None
    
    def generate_from_context_improved(self, message: str, user_id: str = None, 
                                      intent: str = None, words: List[str] = None) -> Optional[str]:
        if not words:
            words = self.extract_words(message)
        
        context_words = self.working_memory.get_context(3)
        
        if not context_words or len(context_words) < 2:
            return None
        
        meaningful_context = [w for w in context_words if len(w) > 3]
        
        if not meaningful_context:
            return None
        
        context_word = meaningful_context[0]
        
        if intent == "question":
            responses = [
                f"Ты спрашиваешь о {context_word}? Это действительно интересно!",
                f"Насчёт {context_word}... это сложная тема.",
                f"{context_word.capitalize()} - хороший вопрос! Что ты сам знаешь об этом?",
                f"Regarding {context_word}... I need more information.",
            ]
            return random.choice(responses)
        
        elif intent == "greeting":
            responses = [
                f"Привет! Говорили о {context_word}?",
                f"Здравствуй! Кстати, о {context_word}...",
                f"Hi! Were we talking about {context_word}?",
            ]
            return random.choice(responses)
        
        elif intent == "statement":
            if words:
                main_word = words[0] if len(words[0]) > 3 else context_word
                responses = [
                    f"Да, {main_word} это важно!",
                    f"Согласен насчёт {main_word}.",
                    f"Интересно, что ты сказал о {main_word}.",
                    f"You mentioned {main_word}. Tell me more.",
                ]
                return random.choice(responses)
        
        if len(context_word) > 3:
            responses = [
                f"Кстати, о {context_word}... что ты думаешь?",
                f"Это напомнило мне о {context_word}.",
                f"Speaking of {context_word}...",
                f"By the way, about {context_word}...",
            ]
            return random.choice(responses)
        
        return None
    
    def transform_to_response(self, found_text: str, original_message: str) -> str:
        if len(found_text) < 10:
            return ""
        
        if found_text.lower() == original_message.lower():
            return ""
        
        if '?' in found_text:
            responses = [
                f"Хм, хороший вопрос из прошлого:",
                f"Кто-то спрашивал похожее:",
                f"Нашёл похожий вопрос:",
            ]
            question_text = found_text.replace('?', '')
            if len(question_text) > 100:
                question_text = question_text[:97] + "..."
            return f"{random.choice(responses)} \"{question_text}\""
        
        if len(found_text.split()) > 3:
            responses = [
                "Нашёл кое-что по теме:",
                "Вот что я знаю:",
                "Похожая информация:",
                "Из моих знаний:",
            ]
            if len(found_text) > 150:
                found_text = found_text[:147] + "..."
            return f"{random.choice(responses)} {found_text}"
        
        return ""
    
    def try_logical_reasoning(self, nouns: List[str], message: str) -> Optional[str]:
        if not nouns:
            return None
        
        main_noun = nouns[0]
        
        properties = self.knowledge_graph.infer(main_noun, "has_property", max_depth=1)
        if properties:
            for prop_name, strength in properties:
                if strength > 0.7 and len(prop_name) > 3:
                    responses = [
                        f"Знаешь, {main_noun} обычно {prop_name}.",
                        f"Кстати, {main_noun} часто бывает {prop_name}.",
                        f"Насчёт {main_noun} - он действительно {prop_name}.",
                        f"I think {main_noun} is usually {prop_name}.",
                    ]
                    return random.choice(responses)
        
        related = self.knowledge_graph.infer(main_noun, "related_to", max_depth=1)
        if related:
            for related_name, strength in related:
                if strength > 0.6 and len(related_name) > 3:
                    responses = [
                        f"{main_noun.capitalize()} связан с {related_name}.",
                        f"Кстати, {main_noun} и {related_name} часто упоминают вместе.",
                        f"Знаешь, {main_noun} обычно ассоциируется с {related_name}.",
                    ]
                    return random.choice(responses)
        
        categories = self.knowledge_graph.infer(main_noun, "is_a", max_depth=1)
        if categories:
            for category, strength in categories:
                if strength > 0.8 and len(category) > 3:
                    responses = [
                        f"{main_noun.capitalize()} является {category}.",
                        f"Кстати, {main_noun} - это вид {category}.",
                        f"Знаешь, {main_noun} относится к {category}.",
                    ]
                    return random.choice(responses)
        
        return None
    
    def get_fallback_response_improved(self, intent: str, message: str, user_id: str = None) -> str:
        message_lower = message.lower()
        
        if len(message.split()) < 3:
            responses = [
                "Понял тебя!",
                "Интересно!",
                "Хм...",
                "Да?",
                "OK.",
                "I see.",
                "Got it.",
            ]
            return random.choice(responses)
        
        if intent == "question":
            responses = [
                "Это сложный вопрос. Дай мне подумать...",
                "Интересно, а что ты сам думаешь?",
                "Хм, хороший вопрос. Мне нужно больше информации.",
                "Сложно ответить однозначно.",
                "That's a tough question. Let me think...",
                "I'm not sure about that. What's your opinion?",
            ]
        elif intent == "statement":
            responses = [
                "Понял, что ты сказал!",
                "Интересная мысль!",
                "Спасибо, что поделился!",
                "Запомнил это!",
                "Thanks for sharing!",
                "That's interesting!",
            ]
        elif intent == "greeting":
            responses = [
                "Рад общению!",
                "Приятно побеседовать!",
                "Good to talk to you!",
                "Nice chatting!",
                "Glad we're talking!",
            ]
        elif intent == "thanks":
            responses = [
                "Всегда рад помочь!",
                "Обращайся!",
                "Anytime!",
                "Happy to help!",
            ]
        else:
            responses = [
                "Продолжай, интересно!",
                "Расскажи ещё!",
                "What else?",
                "Go on...",
                "Tell me more.",
                "Interesting! Continue please.",
            ]
        
        return random.choice(responses)
    
    def cache_response(self, key: str, response: str):
        self.response_cache[key] = response
        
        if len(self.response_cache) > 1000:
            for _ in range(200):
                if self.response_cache:
                    self.response_cache.popitem(last=False)
    
    def update_stats(self, start_time: datetime):
        response_time = (datetime.now() - start_time).total_seconds()
        
        total_responses = self.stats["total_responses"]
        old_avg = self.stats["avg_response_time"]
        
        if total_responses == 0:
            new_avg = response_time
        else:
            new_avg = (old_avg * total_responses + response_time) / (total_responses + 1)
        
        self.stats["total_responses"] += 1
        self.stats["avg_response_time"] = new_avg
        
        self.working_memory.decay(0.98)
    
    def get_stats(self) -> Dict:
        return {
            "total_learned": self.stats["total_learned"],
            "total_responses": self.stats["total_responses"],
            "avg_response_time": round(self.stats["avg_response_time"], 3),
            "active_users": len(self.stats["active_users"]),
            "knowledge_graph_nodes": len(self.knowledge_graph.nodes),
            "working_memory_size": len(self.working_memory.slots),
            "semantic_search_docs": len(self.semantic_search.documents),
            "response_variants": sum(len(v) for v in self.response_variants.values()),
            "user_profiles": len(self.user_profiles),
            "response_cache_size": len(self.response_cache),
        }
    
    def save_to_file(self):
        try:
            data = {
                'knowledge_graph': {},
                'response_variants': {},
                'user_profiles': {},
                'conversation_history': self.conversation_history[-500:],
                'semantic_search': [],
                'classifier_weights': {
                    'W1': self.classifier.W1.tolist(),
                    'b1': self.classifier.b1.tolist(),
                    'W2': self.classifier.W2.tolist(),
                    'b2': self.classifier.b2.tolist(),
                },
                'personality': {
                    'traits': self.personality.traits,
                    'user_adaptations': {k: dict(v) for k, v in self.personality.user_adaptations.items()},
                    'mood': self.personality.mood,
                    'energy': self.personality.energy,
                },
                'stats': {
                    'total_learned': self.stats['total_learned'],
                    'total_responses': self.stats['total_responses'],
                    'avg_response_time': self.stats['avg_response_time'],
                    'active_users': list(self.stats['active_users']),
                    'last_activity': self.stats['last_activity']
                },
                'metadata': {
                    'saved_at': datetime.now().isoformat(),
                    'version': '0.1.0',
                    'total_nodes': len(self.knowledge_graph.nodes),
                }
            }
            
            important_nodes = sorted(
                self.knowledge_graph.nodes.items(),
                key=lambda x: x[1].weight,
                reverse=True
            )[:1000]
            
            for node_id, node in important_nodes:
                data['knowledge_graph'][node_id] = {
                    'name': node.name,
                    'type': node.node_type,
                    'weight': node.weight,
                    'last_accessed': node.last_accessed,
                    'attributes': node.attributes,
                    'relations': dict(node.relations),
                }
            
            for key, variants in self.response_variants.items():
                data['response_variants'][key] = [
                    (resp, weight, list(users)) 
                    for resp, weight, users in variants
                ]
            
            for user_id, profile in self.user_profiles.items():
                data['user_profiles'][user_id] = {
                    'message_count': profile['message_count'],
                    'vocabulary': list(profile['vocabulary'])[:100],
                    'last_message': profile['last_message'],
                    'avg_length': profile['avg_length'],
                    'total_length': profile.get('total_length', 0),
                    'preferred_topics': dict(profile['preferred_topics']),
                }
            
            recent_docs = sorted(
                self.semantic_search.documents,
                key=lambda x: x.get('added_at', ''),
                reverse=True
            )[:500]
            
            for doc in recent_docs:
                data['semantic_search'].append({
                    'text': doc['text'],
                    'tags': list(doc.get('tags', [])),
                    'added_at': doc.get('added_at', datetime.now().isoformat()),
                })
            
            json_data = json.dumps(data, ensure_ascii=False, indent=2, cls=EnhancedJSONEncoder)
            
            try:
                json.loads(json_data)
            except Exception as e:
                print(f"❌ AI: Данные невалидны после сериализации: {e}")
                data['semantic_search'] = []
                json_data = json.dumps(data, ensure_ascii=False, indent=2, cls=EnhancedJSONEncoder)
            
            write_plugin_file("ai_knowledge_v2.json", json_data)
            
            print(f"💾 Ai Algorithm: Сохранено {len(important_nodes)} узлов графа знаний, "
                  f"{len(data['response_variants'])} вариантов ответов, "
                  f"{len(data['user_profiles'])} профилей пользователей")
            return True
            
        except Exception as e:
            print(f"❌ Ai Algorithm: Ошибка сохранения: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_from_file(self):
        try:
            if plugin_file_exists("ai_knowledge_v2.json"):
                content = read_plugin_file("ai_knowledge_v2.json")
                data = json.loads(content)
                
                self.knowledge_graph = KnowledgeGraph()
                for node_id, node_data in data.get('knowledge_graph', {}).items():
                    node = KnowledgeNode(node_data['name'], node_data.get('type', 'concept'))
                    node.weight = node_data.get('weight', 1.0)
                    node.last_accessed = node_data.get('last_accessed', datetime.now().isoformat())
                    node.attributes = node_data.get('attributes', {})
                    node.relations = defaultdict(float, node_data.get('relations', {}))
                    self.knowledge_graph.nodes[node_id] = node
                    self.knowledge_graph.node_by_name[node_data['name']] = node_id
                
                self.response_variants.clear()
                for key, variants in data.get('response_variants', {}).items():
                    self.response_variants[key] = [
                        (resp, weight, set(users)) 
                        for resp, weight, users in variants
                    ]
                
                self.user_profiles.clear()
                for user_id, profile_data in data.get('user_profiles', {}).items():
                    self.user_profiles[user_id] = {
                        'message_count': profile_data.get('message_count', 0),
                        'vocabulary': set(profile_data.get('vocabulary', [])),
                        'last_message': profile_data.get('last_message', ''),
                        'avg_length': profile_data.get('avg_length', 0),
                        'total_length': profile_data.get('total_length', 0),
                        'preferred_topics': defaultdict(int, profile_data.get('preferred_topics', {})),
                    }
                
                self.conversation_history = data.get('conversation_history', [])
                
                if 'classifier_weights' in data:
                    weights = data['classifier_weights']
                    self.classifier.W1 = np.array(weights.get('W1', self.classifier.W1), dtype=np.float32)
                    self.classifier.b1 = np.array(weights.get('b1', self.classifier.b1), dtype=np.float32)
                    self.classifier.W2 = np.array(weights.get('W2', self.classifier.W2), dtype=np.float32)
                    self.classifier.b2 = np.array(weights.get('b2', self.classifier.b2), dtype=np.float32)
                
                if 'personality' in data:
                    personality_data = data['personality']
                    self.personality.traits.update(personality_data.get('traits', {}))
                    self.personality.mood = personality_data.get('mood', 0.5)
                    self.personality.energy = personality_data.get('energy', 0.8)
                    
                    for user_id, adaptations in personality_data.get('user_adaptations', {}).items():
                        self.personality.user_adaptations[user_id] = adaptations
                
                if 'stats' in data:
                    stats_data = data['stats']
                    self.stats = {
                        'total_learned': stats_data.get('total_learned', 0),
                        'total_responses': stats_data.get('total_responses', 0),
                        'avg_response_time': stats_data.get('avg_response_time', 0),
                        'active_users': set(stats_data.get('active_users', [])),
                        'last_activity': stats_data.get('last_activity', datetime.now().isoformat())
                    }
                
                self.semantic_search = FastSemanticSearch()
                for doc_data in data.get('semantic_search', []):
                    self.semantic_search.add_document(
                        doc_data.get('text', ''),
                        doc_data.get('tags', [])
                    )
                
                print(f"✅ Ai Algorithm: Загружено {len(self.knowledge_graph.nodes)} узлов графа знаний, "
                      f"{len(self.response_variants)} вариантов ответов, "
                      f"{len(self.user_profiles)} профилей пользователей")
                return True
                
        except Exception as e:
            print(f"❌ Ai Algorithm: Ошибка загрузки: {e}")
            import traceback
            traceback.print_exc()
        
        return False

class AdvancedAIPlugin:
    def __init__(self):
        self.ai = AdvancedAI()
        self.learning_enabled = True
        self.auto_respond = True
        self.response_probability = 0.15
        self.cooldown = {}
        self.save_counter = 0
        self.auto_save_task = None
    
    def save_knowledge(self):
        try:
            if self.ai.save_to_file():
                print(f"💾 Ai Algorithm: Знания сохранены")
                return True
            else:
                print("❌ Ai Algorithm: Ошибка при сохранении")
                return False
        except Exception as e:
            print(f"❌ Ai Algorithm: Критическая ошибка при сохранении: {e}")
            return False
    
    def is_on_cooldown(self, user_id: str, channel_id: str) -> bool:
        key = f"{user_id}:{channel_id}"
        current_time = datetime.now()
        
        if key in self.cooldown:
            last_response = self.cooldown[key]
            if (current_time - last_response).seconds < 20:
                return True
        
        self.cooldown[key] = current_time
        
        if len(self.cooldown) > 1000:
            keys_to_remove = []
            for k, time in self.cooldown.items():
                if (current_time - time).seconds > 300:
                    keys_to_remove.append(k)
            
            for k in keys_to_remove:
                del self.cooldown[k]
        
        return False

ai_plugin = AdvancedAIPlugin()

@plugin_hook('on_ready')
async def ai_on_ready():
    print(f"🧠 Ai Algorithm: Умный ИИ готов к обучению!")
    
    if ai_plugin.ai.load_from_file():
        stats = ai_plugin.ai.get_stats()
        print(f"📊 Загружено: {stats['knowledge_graph_nodes']} узлов знаний, "
              f"{stats['response_variants']} вариантов ответов, "
              f"{stats['user_profiles']} пользователей")
    else:
        print("ℹ️ Начинаем с чистого листа")
        ai_plugin.save_knowledge()
    
    @tasks.loop(minutes=30)
    async def auto_save():
        try:
            ai_plugin.save_knowledge()
            print("💾 Ai Algorithm: Автосохранение выполнено")
        except Exception as e:
            print(f"❌ Ai Algorithm: Ошибка автосохранения: {e}")
    
    auto_save.start()
    ai_plugin.auto_save_task = auto_save
    
    def shutdown_save():
        print("💾 Ai Algorithm: Сохранение при выходе...")
        try:
            ai_plugin.save_knowledge()
        except:
            pass
    
    atexit.register(shutdown_save)

@plugin_hook('on_message')
async def ai_on_message(message: discord.Message):
    if message.author.bot or not message.content.strip():
        return
    
    if message.content.startswith('/'):
        return
    
    user_id = str(message.author.id)
    channel_id = str(message.channel.id)
    message_text = message.content[:1000]
    
    if ai_plugin.learning_enabled:
        ai_plugin.ai.learn_from_message(user_id, message_text)
        
        ai_plugin.save_counter += 1
        if ai_plugin.save_counter >= 30:
            ai_plugin.save_knowledge()
            ai_plugin.save_counter = 0
    
    if (ai_plugin.auto_respond and 
        random.random() < ai_plugin.response_probability and
        not ai_plugin.is_on_cooldown(user_id, channel_id)):
        
        triggers = ['бот', 'ии', 'ai', 'алгоритм', 'нейросеть', '@бот']
        question_indicators = ['?', 'почему', 'как', 'что', 'зачем']
        
        has_trigger = any(trigger in message_text.lower() for trigger in triggers)
        has_question = any(indicator in message_text.lower() for indicator in question_indicators)
        
        if has_trigger or has_question or len(message_text.split()) >= 10:
            response = ai_plugin.ai.generate_response(message_text, user_id)
            
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            try:
                await message.channel.send(response)
                
                ai_plugin.ai.learn_from_message(user_id, message_text, response)
            except Exception as e:
                print(f"❌ Ошибка отправки сообщения: {e}")

@plugin_command(
    name="ai_chat",
    description="Поговорить с умным ИИ"
)
@app_commands.describe(
    message="Ваше сообщение ИИ"
)
async def ai_chat_command(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    
    user_id = str(interaction.user.id)
    
    response = ai_plugin.ai.generate_response(message, user_id)
    
    ai_plugin.ai.learn_from_message(user_id, message, response)
    
    embed = discord.Embed(
        title="🧠 Алгоритм ИИ",
        description=f"**Вы:** {message[:500]}\n\n**ИИ:** {response}",
        color=0x5865F2
    )
    
    traits = ai_plugin.ai.personality.traits
    dominant_trait = max(traits.items(), key=lambda x: x[1])
    
    embed.add_field(
        name="🎭 Личность ИИ",
        value=f"**Доминирующая черта:** {dominant_trait[0]} ({dominant_trait[1]:.1f})\n"
              f"**Настроение:** {ai_plugin.ai.personality.mood:.1f}\n"
              f"**Энергия:** {ai_plugin.ai.personality.energy:.1f}",
        inline=True
    )
    
    context = ai_plugin.ai.working_memory.get_context(3)
    if context:
        embed.add_field(
            name="📝 Текущий контекст",
            value=", ".join(context[:3]),
            inline=True
        )
    
    embed.set_footer(text=f"🤖 Ai Algorithm | {datetime.now().strftime('%H:%M:%S')}")
    
    await interaction.followup.send(embed=embed)

@plugin_command(
    name="ai_stats",
    description="Статистика обучения ИИ"
)
async def ai_stats_command(interaction: discord.Interaction):
    stats = ai_plugin.ai.get_stats()
    
    embed = discord.Embed(
        title="📊 Статистика Ai Algorithm",
        description="Умный ИИ с самообучением в реальном времени",
        color=0x5865F2
    )
    
    embed.add_field(
        name="🧠 Знания",
        value=f"**Узлов графа знаний:** {stats['knowledge_graph_nodes']:,}\n"
              f"**Вариантов ответов:** {stats['response_variants']:,}\n"
              f"**Документов в поиске:** {stats['semantic_search_docs']:,}",
        inline=True
    )
    
    embed.add_field(
        name="👥 Пользователи",
        value=f"**Активных пользователей:** {stats['active_users']:,}\n"
              f"**Профилей пользователей:** {stats['user_profiles']:,}\n"
              f"**Всего обучений:** {stats['total_learned']:,}",
        inline=True
    )
    
    embed.add_field(
        name="⚡ Производительность",
        value=f"**Среднее время ответа:** {stats['avg_response_time']:.3f}с\n"
              f"**Всего ответов:** {stats['total_responses']:,}\n"
              f"**Размер кэша:** {stats['response_cache_size']:,}",
        inline=True
    )
    
    context = ai_plugin.ai.working_memory.get_context(5)
    if context:
        embed.add_field(
            name="💭 Рабочая память",
            value=", ".join(context),
            inline=False
        )
    
    traits_text = "\n".join([
        f"**{trait}:** {value:.1f}" 
        for trait, value in ai_plugin.ai.personality.traits.items()
    ])
    embed.add_field(name="🎭 Черты личности", value=traits_text, inline=False)
    
    embed.set_footer(text="🤖 Самообучение в реальном времени")
    
    await interaction.response.send_message(embed=embed)

@plugin_command(
    name="ai_teach",
    description="Обучить ИИ конкретному вопросу и ответу"
)
@app_commands.describe(
    question="Вопрос или фраза",
    answer="Правильный ответ"
)
async def ai_teach_command(interaction: discord.Interaction, question: str, answer: str):
    user_id = str(interaction.user.id)
    
    ai_plugin.ai.learn_from_message(user_id, question, answer)
    
    ai_plugin.save_knowledge()
    
    embed = discord.Embed(
        title="✅ ИИ успешно обучен!",
        description=f"**Вопрос:** {question}\n**Ответ:** {answer}",
        color=0x57F287
    )
    
    words = ai_plugin.ai.extract_words(question)
    if words:
        embed.add_field(
            name="📚 Обучено слов",
            value=f"Распознано: {len(words)} слов\nКлючевые: {', '.join(words[:3])}",
            inline=True
        )
    
    stats = ai_plugin.ai.get_stats()
    embed.add_field(
        name="📊 Статистика",
        value=f"Всего обучений: {stats['total_learned']:,}",
        inline=True
    )
    
    embed.set_footer(text="Знание сохранено в базу данных")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@plugin_command(
    name="ai_knowledge",
    description="Поиск в знаниях ИИ"
)
@app_commands.describe(
    query="Что искать в знаниях ИИ"
)
async def ai_knowledge_command(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    
    words = ai_plugin.ai.extract_words(query)
    
    embed = discord.Embed(
        title="🔍 Поиск в знаниях ИИ",
        description=f"Запрос: {query}",
        color=0xFEE75C
    )
    
    if words:
        for word in words[:2]:
            properties = ai_plugin.ai.knowledge_graph.infer(word, "has_property", max_depth=1)
            related = ai_plugin.ai.knowledge_graph.infer(word, "related_to", max_depth=1)
            
            if properties:
                prop_text = ", ".join([p[0] for p in properties[:3]])
                embed.add_field(
                    name=f"📝 Свойства '{word}'",
                    value=prop_text,
                    inline=False
                )
            
            if related:
                rel_text = ", ".join([r[0] for r in related[:3]])
                embed.add_field(
                    name=f"🔗 Связано с '{word}'",
                    value=rel_text,
                    inline=False
                )
    
    search_results = ai_plugin.ai.semantic_search.search(query, k=3)
    if search_results:
        results_text = "\n".join([
            f"• {text[:80]}..." if len(text) > 80 else f"• {text}"
            for score, text in search_results[:3]
        ])
        embed.add_field(
            name="📚 Похожие знания",
            value=results_text,
            inline=False
        )
    
    if len(embed.fields) == 0:
        embed.description = "Пока нет знаний по этому запросу. Задайте вопрос, и ИИ научится!"
    
    await interaction.followup.send(embed=embed)

@plugin_command(
    name="ai_debug",
    description="Отладочная информация об ИИ"
)
@app_commands.default_permissions(administrator=True)
async def ai_debug_command(interaction: discord.Interaction):
    await interaction.response.defer()
    
    stats = ai_plugin.ai.get_stats()
    
    embed = discord.Embed(
        title="🐛 Отладочная информация Ai Algorithm",
        description="Детальная информация о состоянии ИИ",
        color=0x5865F2
    )
    
    embed.add_field(
        name="⚙️ Система",
        value=f"**Learning Rate:** {ai_plugin.ai.learning_rate}\n"
              f"**Auto Respond:** {ai_plugin.auto_respond}\n"
              f"**Response Probability:** {ai_plugin.response_probability}\n"
              f"**Save Counter:** {ai_plugin.save_counter}/30",
        inline=False
    )
    
    embed.add_field(
        name="⚡ Производительность",
        value=f"**Кэш ответов:** {stats['response_cache_size']}\n"
              f"**Кэш классификатора:** {len(ai_plugin.ai.classifier.vector_cache)}\n"
              f"**Кэш семантики:** {len(ai_plugin.ai.semantic_search.embedding_cache)}\n"
              f"**Cooldown записей:** {len(ai_plugin.cooldown)}",
        inline=False
    )
    
    embed.add_field(
        name="💾 Память",
        value=f"**Рабочая память:** {len(ai_plugin.ai.working_memory.slots)}/{ai_plugin.ai.working_memory.capacity}\n"
              f"**Фокус внимания:** {ai_plugin.ai.working_memory.current_focus or 'Нет'}\n"
              f"**Инвертированный индекс:** {len(ai_plugin.ai.semantic_search.inverted_index)} слов",
        inline=False
    )
    
    if ai_plugin.ai.knowledge_graph.nodes:
        node_counts = defaultdict(int)
        for node in ai_plugin.ai.knowledge_graph.nodes.values():
            node_counts[node.node_type] += 1
        
        graph_text = "\n".join([f"**{type_}:** {count}" for type_, count in node_counts.items()])
        embed.add_field(name="🌐 Граф знаний", value=graph_text, inline=False)
    
    embed.set_footer(text=f"🤖 Ai Algorithm | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await interaction.followup.send(embed=embed)

@plugin_command(
    name="ai_personality",
    description="Настроить личность ИИ"
)
@app_commands.describe(
    trait="Черта личности",
    value="Значение (0.0-1.0)"
)
async def ai_personality_command(interaction: discord.Interaction, trait: str, value: float):
    if trait not in ai_plugin.ai.personality.traits:
        await interaction.response.send_message(
            f"❌ Неизвестная черта личности. Доступные: {', '.join(ai_plugin.ai.personality.traits.keys())}",
            ephemeral=True
        )
        return
    
    value = max(0.0, min(1.0, value))
    
    old_value = ai_plugin.ai.personality.traits[trait]
    ai_plugin.ai.personality.traits[trait] = value
    
    embed = discord.Embed(
        title="🎭 Личность ИИ обновлена",
        description=f"**Черта:** {trait}\n**Было:** {old_value:.2f}\n**Стало:** {value:.2f}",
        color=0xEB459E
    )
    
    trait_descriptions = {
        "formality": "Формальность общения (0.0 - неформальный, 1.0 - формальный)",
        "humor": "Склонность к юмору (0.0 - серьёзный, 1.0 - шутливый)",
        "curiosity": "Любознательность (0.0 - пассивный, 1.0 - любопытный)",
        "empathy": "Эмпатия (0.0 - нейтральный, 1.0 - эмпатичный)",
        "enthusiasm": "Энтузиазм (0.0 - спокойный, 1.0 - энергичный)",
        "sarcasm": "Сарказм (0.0 - прямой, 1.0 - саркастичный)",
        "creativity": "Креативность (0.0 - логичный, 1.0 - креативный)",
    }
    
    if trait in trait_descriptions:
        embed.add_field(name="📝 Описание", value=trait_descriptions[trait], inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@plugin_command(
    name="ai_save",
    description="Принудительно сохранить знания ИИ"
)
@app_commands.default_permissions(administrator=True)
async def ai_save_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    success = ai_plugin.save_knowledge()
    
    if success:
        stats = ai_plugin.ai.get_stats()
        await interaction.followup.send(
            f"✅ Знания сохранены!\n\n"
            f"📊 **Узлов графа знаний:** {stats['knowledge_graph_nodes']:,}\n"
            f"💬 **Вариантов ответов:** {stats['response_variants']:,}\n"
            f"👥 **Профилей пользователей:** {stats['user_profiles']:,}\n"
            f"🧠 **Всего обучений:** {stats['total_learned']:,}",
            ephemeral=True
        )
    else:
        await interaction.followup.send("❌ Ошибка при сохранении знаний", ephemeral=True)

@plugin_command(
    name="ai_reset",
    description="Сбросить базу знаний ИИ (только для админов)"
)
@app_commands.default_permissions(administrator=True)
async def ai_reset_command(interaction: discord.Interaction):
    confirm_embed = discord.Embed(
        title="⚠️ Подтверждение сброса",
        description="**Вы уверены, что хотите сбросить всю базу знаний ИИ?**\n\n"
                   "Это действие нельзя отменить!\n"
                   "Все обученные данные будут удалены:\n"
                   "• Граф знаний\n• Варианты ответов\n• Профили пользователей\n• История\n"
                   "• Настройки личности\n\n"
                   "**ИИ начнет обучение с чистого листа.**",
        color=0xED4245
    )
    
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
        
        @discord.ui.button(label="✅ Да, сбросить все", style=discord.ButtonStyle.danger, emoji="🗑️")
        async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("❌ Это не ваша кнопка!", ephemeral=True)
                return
            
            ai_plugin.ai = AdvancedAI()
            ai_plugin.save_knowledge()
            
            success_embed = discord.Embed(
                title="🔄 База знаний полностью сброшена",
                description="ИИ начал обучение с чистого листа!\n\n"
                           "Все предыдущие данные удалены.\n"
                           "Готов к новому обучению!",
                color=0x57F287
            )
            await button_interaction.response.send_message(embed=success_embed)
            self.stop()
        
        @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary, emoji="↩️")
        async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("❌ Это не ваша кнопка!", ephemeral=True)
                return
            
            cancel_embed = discord.Embed(
                title="✅ Отменено",
                description="Сброс базы знаний отменен.\n\n"
                           "Все данные сохранены.",
                color=0x808080
            )
            await button_interaction.response.send_message(embed=cancel_embed)
            self.stop()
    
    await interaction.response.send_message(embed=confirm_embed, view=ConfirmView(), ephemeral=True)

@plugin_hook('before_command')
async def ai_before_command(interaction: discord.Interaction):
    try:
        user_id = str(interaction.user.id)
        command_name = interaction.command.name if interaction.command else "unknown"
        
        ai_plugin.ai.learn_from_message(user_id, f"команда {command_name}")
    except Exception as e:
        print(f"❌ AI: Ошибка в before_command: {e}")

print("🧠 Ai Algorithm: Умный ИИ с самообучением готов к работе!")
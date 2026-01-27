#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
СИСТЕМА СООБЩЕНИЙ - API Endpoints
Полноценный мессенджер между донорами и медцентрами
"""

from datetime import datetime, timedelta
from flask import jsonify, request, g
from functools import wraps


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_or_create_conversation(donor_id, medical_center_id, query_db_func):
    """Получить или создать диалог между донором и медцентром"""
    conversation = query_db_func(
        """SELECT * FROM conversations 
           WHERE donor_id = %s AND medical_center_id = %s""",
        (donor_id, medical_center_id), one=True
    )
    
    if not conversation:
        query_db_func(
            """INSERT INTO conversations (donor_id, medical_center_id, created_at, updated_at)
               VALUES (%s, %s, NOW(), NOW())""",
            (donor_id, medical_center_id), commit=True
        )
        conversation = query_db_func(
            """SELECT * FROM conversations 
               WHERE donor_id = %s AND medical_center_id = %s""",
            (donor_id, medical_center_id), one=True
        )
    
    return conversation


def format_conversation(conv, partner_info, unread_count, query_db_func):
    """Форматировать диалог для отправки клиенту"""
    # 🔧 FIX: Используем last_msg_time если есть, иначе last_message_at
    last_time = conv.get('last_msg_time') or conv.get('last_message_at')
    last_time_str = last_time.isoformat() if last_time else None
    
    # 🔧 FIX: Берём превью из подзапроса или из колонки таблицы
    preview = conv.get('last_message_preview') or ''
    
    return {
        'id': conv['id'],
        'partner': {
            'id': partner_info['id'],
            'name': partner_info.get('full_name') or partner_info.get('name'),
            'type': partner_info.get('type', 'medical_center'),
            'blood_type': partner_info.get('blood_type'),
            'donation_count': partner_info.get('donation_count', 0),
            'avatar': get_avatar_initials(partner_info.get('full_name') or partner_info.get('name')),
            # Дополнительная информация о партнёре
            'address': partner_info.get('address'),
            'phone': partner_info.get('phone'),
            'email': partner_info.get('email')
        },
        'last_message': {
            'id': conv.get('last_msg_id'),
            'preview': preview,
            'content': preview,  # 🔧 FIX: Дублируем для совместимости с фронтом
            'time': last_time_str,
            'created_at': last_time_str  # 🔧 FIX: Дублируем для совместимости
        },
        'unread_count': unread_count,
        'status': conv.get('status', 'active'),
        'created_at': conv['created_at'].isoformat() if conv.get('created_at') else None,
        'updated_at': conv['updated_at'].isoformat() if conv.get('updated_at') else None
    }


def get_avatar_initials(name):
    """Получить инициалы для аватара"""
    if not name:
        return '??'
    
    words = name.strip().split()
    if len(words) >= 2:
        return f"{words[0][0]}{words[1][0]}".upper()
    elif len(words) == 1:
        return words[0][:2].upper()
    return '??'


def format_message(msg):
    """Форматировать сообщение для отправки клиенту"""
    return {
        'id': msg['id'],
        'conversation_id': msg['conversation_id'],
        'sender_id': msg.get('sender_id'),
        'sender_type': msg.get('sender_type'),  # Изменено с sender_role
        'content': msg.get('message_text'),  # Изменено с content
        'type': msg.get('message_type', 'text'),
        'is_read': msg.get('is_read', False),
        'created_at': msg['created_at'].isoformat() if msg.get('created_at') else None
    }


# ============================================
# API: СПИСОК ДИАЛОГОВ
# ============================================

def get_conversations_endpoint(require_auth_func, query_db_func):
    """GET /api/messages/conversations - Список диалогов"""
    @require_auth_func()
    def get_conversations():
        user_type = g.session.get('user_type')
        user_id = g.session.get('user_id')
        medical_center_id = g.session.get('medical_center_id')
        
        # Параметры запроса
        status = request.args.get('status', 'active')
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))
        
        if user_type == 'donor':
            # Диалоги донора с медцентрами
            conversations = query_db_func(
                """SELECT c.*, 
                          c.donor_unread_count as unread_count,
                          mc.id as partner_id,
                          mc.name as partner_name,
                          mc.address,
                          mc.phone
                   FROM conversations c
                   JOIN medical_centers mc ON c.medical_center_id = mc.id
                   WHERE c.donor_id = %s AND c.status = %s
                   ORDER BY c.last_message_at DESC NULLS LAST
                   LIMIT %s OFFSET %s""",
                (user_id, status, limit, offset)
            )
            
            result = []
            for conv in conversations:
                partner_info = {
                    'id': conv['partner_id'],
                    'name': conv['partner_name'],
                    'type': 'medical_center',
                    'address': conv.get('address'),
                    'phone': conv.get('phone')
                }
                result.append(format_conversation(conv, partner_info, conv['unread_count'], query_db_func))
            
            return jsonify({'conversations': result, 'total': len(result)})
        
        elif user_type == 'medcenter':
            # Диалоги медцентра с донорами
            conversations = query_db_func(
                """SELECT c.*, 
                          c.medcenter_unread_count as unread_count,
                          u.id as partner_id,
                          u.full_name as partner_name,
                          u.blood_type,
                          u.donation_count
                   FROM conversations c
                   JOIN users u ON c.donor_id = u.id
                   WHERE c.medical_center_id = %s AND c.status = %s
                   ORDER BY c.last_message_at DESC NULLS LAST
                   LIMIT %s OFFSET %s""",
                (medical_center_id, status, limit, offset)
            )
            
            result = []
            for conv in conversations:
                partner_info = {
                    'id': conv['partner_id'],
                    'full_name': conv['partner_name'],
                    'type': 'donor',
                    'blood_type': conv.get('blood_type'),
                    'donation_count': conv.get('donation_count', 0)
                }
                result.append(format_conversation(conv, partner_info, conv['unread_count'], query_db_func))
            
            return jsonify({'conversations': result, 'total': len(result)})
        
        return jsonify({'error': 'Неизвестный тип пользователя'}), 400
    
    return get_conversations


# ============================================
# API: ПОЛУЧИТЬ ОДИН ДИАЛОГ
# ============================================

def get_conversation_endpoint(require_auth_func, query_db_func):
    """GET /api/messages/conversations/<id> - Один диалог"""
    @require_auth_func()
    def get_conversation(conversation_id):
        user_type = g.session.get('user_type')
        user_id = g.session.get('user_id')
        medical_center_id = g.session.get('medical_center_id')
        
        # Проверяем доступ
        if user_type == 'donor':
            conversation = query_db_func(
                """SELECT c.*, 
                          mc.id as partner_id,
                          mc.name as partner_name,
                          mc.address,
                          mc.phone
                   FROM conversations c
                   JOIN medical_centers mc ON c.medical_center_id = mc.id
                   WHERE c.id = %s AND c.donor_id = %s""",
                (conversation_id, user_id), one=True
            )
            
            if not conversation:
                return jsonify({'error': 'Диалог не найден'}), 404
            
            partner_info = {
                'id': conversation['partner_id'],
                'name': conversation['partner_name'],
                'type': 'medical_center',
                'address': conversation.get('address'),
                'phone': conversation.get('phone')
            }
            unread_count = conversation.get('donor_unread_count', 0)
        
        elif user_type == 'medcenter':
            conversation = query_db_func(
                """SELECT c.*, 
                          u.id as partner_id,
                          u.full_name as partner_name,
                          u.blood_type,
                          u.donation_count,
                          u.phone,
                          u.email
                   FROM conversations c
                   JOIN users u ON c.donor_id = u.id
                   WHERE c.id = %s AND c.medical_center_id = %s""",
                (conversation_id, medical_center_id), one=True
            )
            
            if not conversation:
                return jsonify({'error': 'Диалог не найден'}), 404
            
            partner_info = {
                'id': conversation['partner_id'],
                'full_name': conversation['partner_name'],
                'type': 'donor',
                'blood_type': conversation.get('blood_type'),
                'donation_count': conversation.get('donation_count', 0),
                'phone': conversation.get('phone'),
                'email': conversation.get('email')
            }
            unread_count = conversation.get('medcenter_unread_count', 0)
        
        else:
            return jsonify({'error': 'Неизвестный тип пользователя'}), 400
        
        return jsonify(format_conversation(conversation, partner_info, unread_count, query_db_func))
    
    return get_conversation


# ============================================
# API: СОЗДАТЬ ДИАЛОГ
# ============================================

def create_conversation_endpoint(require_auth_func, query_db_func):
    """POST /api/messages/conversations - Создать новый диалог"""
    @require_auth_func()
    def create_conversation():
        data = request.json
        recipient_id = data.get('recipient_id')
        recipient_type = data.get('recipient_type', 'medical_center')
        
        if not recipient_id:
            return jsonify({'error': 'Не указан получатель'}), 400
        
        user_type = g.session.get('user_type')
        user_id = g.session.get('user_id')
        medical_center_id = g.session.get('medical_center_id')
        
        if user_type == 'donor':
            # Донор создаёт диалог с медцентром
            conversation = get_or_create_conversation(user_id, recipient_id, query_db_func)
        
        elif user_type == 'medcenter':
            # Медцентр создаёт диалог с донором
            conversation = get_or_create_conversation(recipient_id, medical_center_id, query_db_func)
        
        else:
            return jsonify({'error': 'Неизвестный тип пользователя'}), 400
        
        return jsonify({'conversation_id': conversation['id'], 'message': 'Диалог создан'}), 201
    
    return create_conversation


# ============================================
# API: АРХИВИРОВАТЬ ДИАЛОГ
# ============================================

def archive_conversation_endpoint(require_auth_func, query_db_func):
    """PUT /api/messages/conversations/<id>/archive"""
    @require_auth_func()
    def archive_conversation(conversation_id):
        user_type = g.session.get('user_type')
        user_id = g.session.get('user_id')
        medical_center_id = g.session.get('medical_center_id')
        
        # Проверяем доступ
        if user_type == 'donor':
            conversation = query_db_func(
                "SELECT id FROM conversations WHERE id = %s AND donor_id = %s",
                (conversation_id, user_id), one=True
            )
        elif user_type == 'medcenter':
            conversation = query_db_func(
                "SELECT id FROM conversations WHERE id = %s AND medical_center_id = %s",
                (conversation_id, medical_center_id), one=True
            )
        else:
            return jsonify({'error': 'Неизвестный тип пользователя'}), 400
        
        if not conversation:
            return jsonify({'error': 'Диалог не найден'}), 404
        
        query_db_func(
            "UPDATE conversations SET status = 'archived', updated_at = NOW() WHERE id = %s",
            (conversation_id,), commit=True
        )
        
        return jsonify({'message': 'Диалог архивирован'})
    
    return archive_conversation


def unarchive_conversation_endpoint(require_auth_func, query_db_func):
    """PUT /api/messages/conversations/<id>/unarchive"""
    @require_auth_func()
    def unarchive_conversation(conversation_id):
        user_type = g.session.get('user_type')
        user_id = g.session.get('user_id')
        medical_center_id = g.session.get('medical_center_id')
        
        # Проверяем доступ
        if user_type == 'donor':
            conversation = query_db_func(
                "SELECT id FROM conversations WHERE id = %s AND donor_id = %s",
                (conversation_id, user_id), one=True
            )
        elif user_type == 'medcenter':
            conversation = query_db_func(
                "SELECT id FROM conversations WHERE id = %s AND medical_center_id = %s",
                (conversation_id, medical_center_id), one=True
            )
        else:
            return jsonify({'error': 'Неизвестный тип пользователя'}), 400
        
        if not conversation:
            return jsonify({'error': 'Диалог не найден'}), 404
        
        query_db_func(
            "UPDATE conversations SET status = 'active', updated_at = NOW() WHERE id = %s",
            (conversation_id,), commit=True
        )
        
        return jsonify({'message': 'Диалог восстановлен'})
    
    return unarchive_conversation

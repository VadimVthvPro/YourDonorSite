#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
СИСТЕМА СООБЩЕНИЙ - API Endpoints (Часть 2: Сообщения)
"""

from datetime import datetime
from flask import jsonify, request, g


# ============================================
# API: СПИСОК СООБЩЕНИЙ В ДИАЛОГЕ
# ============================================

def get_messages_endpoint(require_auth_func, query_db_func):
    """GET /api/messages/conversations/<id>/messages - Сообщения в диалоге"""
    @require_auth_func()
    def get_messages(conversation_id):
        user_type = g.session.get('user_type')
        user_id = g.session.get('user_id')
        medical_center_id = g.session.get('medical_center_id')
        
        # Проверяем доступ к диалогу
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
        
        # Параметры пагинации
        limit = min(int(request.args.get('limit', 50)), 100)
        before_id = request.args.get('before_id')  # Для загрузки истории
        
        # Запрос сообщений
        if before_id:
            messages = query_db_func(
                """SELECT * FROM messages 
                   WHERE conversation_id = %s 
                     AND deleted_at IS NULL 
                     AND id < %s
                   ORDER BY created_at DESC 
                   LIMIT %s""",
                (conversation_id, before_id, limit)
            )
        else:
            messages = query_db_func(
                """SELECT * FROM messages 
                   WHERE conversation_id = %s 
                     AND deleted_at IS NULL
                   ORDER BY created_at DESC 
                   LIMIT %s""",
                (conversation_id, limit)
            )
        
        # Форматируем сообщения
        from messaging_api import format_message
        result = [format_message(msg) for msg in messages]
        
        # Возвращаем в прямом хронологическом порядке
        result.reverse()
        
        return jsonify({'messages': result, 'count': len(result)})
    
    return get_messages


# ============================================
# API: ОТПРАВИТЬ СООБЩЕНИЕ
# ============================================

def send_message_endpoint(require_auth_func, query_db_func, app_logger, send_telegram_notification=None):
    """POST /api/messages/conversations/<id>/messages - Отправить сообщение"""
    @require_auth_func()
    def send_message(conversation_id):
        data = request.json
        content = data.get('content', '').strip()
        message_type = data.get('type', 'text')
        metadata = data.get('metadata')
        
        if not content:
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400
        
        user_type = g.session.get('user_type')
        user_id = g.session.get('user_id')
        medical_center_id = g.session.get('medical_center_id')
        
        # Проверяем доступ к диалогу
        if user_type == 'donor':
            conversation = query_db_func(
                "SELECT * FROM conversations WHERE id = %s AND donor_id = %s",
                (conversation_id, user_id), one=True
            )
            sender_id = user_id
            sender_role = 'donor'
        elif user_type == 'medcenter':
            conversation = query_db_func(
                "SELECT * FROM conversations WHERE id = %s AND medical_center_id = %s",
                (conversation_id, medical_center_id), one=True
            )
            sender_id = None  # медцентр не имеет user_id
            sender_role = 'medical_center'
        else:
            return jsonify({'error': 'Неизвестный тип пользователя'}), 400
        
        if not conversation:
            return jsonify({'error': 'Диалог не найден'}), 404
        
        # Создаём сообщение
        query_db_func(
            """INSERT INTO messages 
               (conversation_id, sender_id, sender_role, content, message_type, metadata, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
            (conversation_id, sender_id, sender_role, content, message_type, 
             metadata if metadata else None),
            commit=True
        )
        
        # Получаем созданное сообщение
        message = query_db_func(
            """SELECT * FROM messages 
               WHERE conversation_id = %s 
               ORDER BY created_at DESC 
               LIMIT 1""",
            (conversation_id,), one=True
        )
        
        app_logger.info(f"✅ Сообщение отправлено: {sender_role} -> conversation {conversation_id}")
        
        # Отправляем уведомление в Telegram (если получатель оффлайн)
        if send_telegram_notification and sender_role == 'medical_center':
            try:
                # Получаем донора и проверяем его активность
                donor = query_db_func(
                    """SELECT u.*, tlc.telegram_id 
                       FROM users u
                       LEFT JOIN telegram_link_codes tlc ON u.id = tlc.user_id AND tlc.linked = TRUE
                       WHERE u.id = %s""",
                    (conversation['donor_id'],), one=True
                )
                
                if donor and donor.get('telegram_id'):
                    # TODO: Проверить, был ли донор онлайн за последние 5 минут
                    # Для простоты пока отправляем всегда
                    medcenter = query_db_func(
                        "SELECT name FROM medical_centers WHERE id = %s",
                        (conversation['medical_center_id'],), one=True
                    )
                    
                    telegram_message = f"💬 Новое сообщение\n\nОт: {medcenter['name']}\n\n\"{content[:100]}{'...' if len(content) > 100 else ''}\"\n\n👉 Ответить на сайте"
                    send_telegram_notification(donor['telegram_id'], telegram_message)
            except Exception as e:
                app_logger.error(f"Ошибка отправки Telegram: {e}")
        
        from messaging_api import format_message
        return jsonify(format_message(message)), 201
    
    return send_message


# ============================================
# API: РЕДАКТИРОВАТЬ СООБЩЕНИЕ
# ============================================

def edit_message_endpoint(require_auth_func, query_db_func):
    """PUT /api/messages/messages/<id> - Редактировать сообщение"""
    @require_auth_func()
    def edit_message(message_id):
        data = request.json
        new_content = data.get('content', '').strip()
        
        if not new_content:
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400
        
        user_type = g.session.get('user_type')
        user_id = g.session.get('user_id')
        medical_center_id = g.session.get('medical_center_id')
        
        # Получаем сообщение
        message = query_db_func(
            "SELECT * FROM messages WHERE id = %s AND deleted_at IS NULL",
            (message_id,), one=True
        )
        
        if not message:
            return jsonify({'error': 'Сообщение не найдено'}), 404
        
        # Проверяем права: только свои сообщения типа 'text'
        if message['message_type'] != 'text':
            return jsonify({'error': 'Можно редактировать только обычные сообщения'}), 403
        
        if user_type == 'donor' and message['sender_role'] != 'donor':
            return jsonify({'error': 'Вы не можете редактировать это сообщение'}), 403
        
        if user_type == 'medcenter' and message['sender_role'] != 'medical_center':
            return jsonify({'error': 'Вы не можете редактировать это сообщение'}), 403
        
        # Обновляем сообщение
        query_db_func(
            """UPDATE messages 
               SET content = %s, edited_at = NOW() 
               WHERE id = %s""",
            (new_content, message_id), commit=True
        )
        
        # Получаем обновлённое сообщение
        updated_message = query_db_func(
            "SELECT * FROM messages WHERE id = %s",
            (message_id,), one=True
        )
        
        from messaging_api import format_message
        return jsonify(format_message(updated_message))
    
    return edit_message


# ============================================
# API: УДАЛИТЬ СООБЩЕНИЕ
# ============================================

def delete_message_endpoint(require_auth_func, query_db_func):
    """DELETE /api/messages/messages/<id> - Удалить сообщение (soft delete)"""
    @require_auth_func()
    def delete_message(message_id):
        user_type = g.session.get('user_type')
        user_id = g.session.get('user_id')
        medical_center_id = g.session.get('medical_center_id')
        
        # Получаем сообщение
        message = query_db_func(
            "SELECT * FROM messages WHERE id = %s AND deleted_at IS NULL",
            (message_id,), one=True
        )
        
        if not message:
            return jsonify({'error': 'Сообщение не найдено'}), 404
        
        # Проверяем права: только свои сообщения типа 'text'
        if message['message_type'] != 'text':
            return jsonify({'error': 'Можно удалять только обычные сообщения'}), 403
        
        if user_type == 'donor' and message['sender_role'] != 'donor':
            return jsonify({'error': 'Вы не можете удалить это сообщение'}), 403
        
        if user_type == 'medcenter' and message['sender_role'] != 'medical_center':
            return jsonify({'error': 'Вы не можете удалить это сообщение'}), 403
        
        # Мягкое удаление
        query_db_func(
            "UPDATE messages SET deleted_at = NOW() WHERE id = %s",
            (message_id,), commit=True
        )
        
        return jsonify({'message': 'Сообщение удалено'})
    
    return delete_message


# ============================================
# API: ОТМЕТИТЬ КАК ПРОЧИТАННОЕ
# ============================================

def mark_conversation_read_endpoint(require_auth_func, query_db_func):
    """POST /api/messages/conversations/<id>/read - Отметить все сообщения как прочитанные"""
    @require_auth_func()
    def mark_conversation_read(conversation_id):
        user_type = g.session.get('user_type')
        user_id = g.session.get('user_id')
        medical_center_id = g.session.get('medical_center_id')
        
        # Проверяем доступ
        if user_type == 'donor':
            conversation = query_db_func(
                "SELECT id FROM conversations WHERE id = %s AND donor_id = %s",
                (conversation_id, user_id), one=True
            )
            # Отмечаем сообщения от медцентра и системы
            query_db_func(
                """UPDATE messages 
                   SET is_read = TRUE, read_at = NOW() 
                   WHERE conversation_id = %s 
                     AND is_read = FALSE 
                     AND sender_role IN ('medical_center', 'system')""",
                (conversation_id,), commit=True
            )
        elif user_type == 'medcenter':
            conversation = query_db_func(
                "SELECT id FROM conversations WHERE id = %s AND medical_center_id = %s",
                (conversation_id, medical_center_id), one=True
            )
            # Отмечаем сообщения от донора
            query_db_func(
                """UPDATE messages 
                   SET is_read = TRUE, read_at = NOW() 
                   WHERE conversation_id = %s 
                     AND is_read = FALSE 
                     AND sender_role = 'donor'""",
                (conversation_id,), commit=True
            )
        else:
            return jsonify({'error': 'Неизвестный тип пользователя'}), 400
        
        if not conversation:
            return jsonify({'error': 'Диалог не найден'}), 404
        
        return jsonify({'message': 'Сообщения отмечены как прочитанные'})
    
    return mark_conversation_read


def mark_message_read_endpoint(require_auth_func, query_db_func):
    """POST /api/messages/messages/<id>/read - Отметить одно сообщение как прочитанное"""
    @require_auth_func()
    def mark_message_read(message_id):
        user_type = g.session.get('user_type')
        
        message = query_db_func(
            "SELECT * FROM messages WHERE id = %s",
            (message_id,), one=True
        )
        
        if not message:
            return jsonify({'error': 'Сообщение не найдено'}), 404
        
        # Проверяем, что сообщение не от текущего пользователя
        if user_type == 'donor' and message['sender_role'] == 'donor':
            return jsonify({'error': 'Нельзя отметить своё сообщение'}), 400
        
        if user_type == 'medcenter' and message['sender_role'] == 'medical_center':
            return jsonify({'error': 'Нельзя отметить своё сообщение'}), 400
        
        # Отмечаем как прочитанное
        query_db_func(
            """UPDATE messages 
               SET is_read = TRUE, read_at = NOW() 
               WHERE id = %s""",
            (message_id,), commit=True
        )
        
        return jsonify({'message': 'Сообщение прочитано'})
    
    return mark_message_read


# ============================================
# API: LONG POLLING ДЛЯ ОБНОВЛЕНИЙ
# ============================================

def get_updates_endpoint(require_auth_func, query_db_func):
    """GET /api/messages/updates - Получить новые сообщения (long polling)"""
    @require_auth_func()
    def get_updates():
        user_type = g.session.get('user_type')
        user_id = g.session.get('user_id')
        medical_center_id = g.session.get('medical_center_id')
        
        last_id = request.args.get('last_id', type=int, default=0)
        since = request.args.get('since')  # ISO timestamp
        
        # Получаем новые сообщения
        if user_type == 'donor':
            # Сообщения в диалогах донора
            messages = query_db_func(
                """SELECT m.* 
                   FROM messages m
                   JOIN conversations c ON m.conversation_id = c.id
                   WHERE c.donor_id = %s 
                     AND m.id > %s
                     AND m.deleted_at IS NULL
                   ORDER BY m.created_at ASC
                   LIMIT 50""",
                (user_id, last_id)
            )
            
            # Обновлённые счётчики
            unread_counts = query_db_func(
                """SELECT id, donor_unread_count as unread_count
                   FROM conversations
                   WHERE donor_id = %s AND donor_unread_count > 0""",
                (user_id,)
            )
        
        elif user_type == 'medcenter':
            # Сообщения в диалогах медцентра
            messages = query_db_func(
                """SELECT m.* 
                   FROM messages m
                   JOIN conversations c ON m.conversation_id = c.id
                   WHERE c.medical_center_id = %s 
                     AND m.id > %s
                     AND m.deleted_at IS NULL
                   ORDER BY m.created_at ASC
                   LIMIT 50""",
                (medical_center_id, last_id)
            )
            
            # Обновлённые счётчики
            unread_counts = query_db_func(
                """SELECT id, medcenter_unread_count as unread_count
                   FROM conversations
                   WHERE medical_center_id = %s AND medcenter_unread_count > 0""",
                (medical_center_id,)
            )
        
        else:
            return jsonify({'error': 'Неизвестный тип пользователя'}), 400
        
        from messaging_api import format_message
        formatted_messages = [format_message(msg) for msg in messages]
        
        return jsonify({
            'messages': formatted_messages,
            'unread_counts': {str(row['id']): row['unread_count'] for row in unread_counts},
            'timestamp': datetime.now().isoformat()
        })
    
    return get_updates

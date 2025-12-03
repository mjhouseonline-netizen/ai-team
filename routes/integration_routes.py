# ==============================================
# ADD THESE ROUTES TO web_app_auth.py
# ==============================================

"""
Integration Routes - Add these to web_app_auth.py
"""

from integrations import integrations_manager

# Import at top of file
# from integrations import integrations_manager

# Add these routes:

@app.route('/integrations')
@login_required
def integrations_page():
    """Integrations settings page"""
    return render_template('integrations.html', user=current_user)

@app.route('/api/integrations')
@login_required
def get_integrations():
    """Get all user integrations"""
    try:
        integrations = integrations_manager.get_all_integrations(current_user.id)
        return jsonify({
            'success': True,
            'integrations': integrations
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/save', methods=['POST'])
@login_required
def save_integration():
    """Save integration credentials"""
    try:
        data = request.json
        integration_type = data.get('integration_type')
        api_key = data.get('api_key')
        access_token = data.get('access_token')
        
        if not integration_type:
            return jsonify({
                'success': False,
                'error': 'Integration type required'
            }), 400
        
        success = integrations_manager.save_integration(
            user_id=current_user.id,
            integration_type=integration_type,
            api_key=api_key,
            access_token=access_token
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save integration'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/delete/<integration_type>', methods=['DELETE'])
@login_required
def delete_integration(integration_type):
    """Delete integration"""
    try:
        success = integrations_manager.delete_integration(
            user_id=current_user.id,
            integration_type=integration_type
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete integration'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/generate-image', methods=['POST'])
@login_required
def generate_image_api():
    """Generate image with DALL-E"""
    try:
        data = request.json
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Prompt required'
            }), 400
        
        image_url = integrations_manager.generate_image(
            user_id=current_user.id,
            prompt=prompt
        )
        
        if image_url:
            return jsonify({
                'success': True,
                'image_url': image_url
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to generate image. Make sure OpenAI is connected.'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/post-facebook', methods=['POST'])
@login_required
def post_facebook_api():
    """Post to Facebook"""
    try:
        data = request.json
        message = data.get('message')
        image_url = data.get('image_url')
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message required'
            }), 400
        
        post_id = integrations_manager.post_to_facebook(
            user_id=current_user.id,
            message=message,
            image_url=image_url
        )
        
        if post_id:
            return jsonify({
                'success': True,
                'post_id': post_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to post. Make sure Facebook is connected.'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/post-instagram', methods=['POST'])
@login_required
def post_instagram_api():
    """Post to Instagram"""
    try:
        data = request.json
        image_url = data.get('image_url')
        caption = data.get('caption')
        
        if not image_url or not caption:
            return jsonify({
                'success': False,
                'error': 'Image URL and caption required'
            }), 400
        
        post_id = integrations_manager.post_to_instagram(
            user_id=current_user.id,
            image_url=image_url,
            caption=caption
        )
        
        if post_id:
            return jsonify({
                'success': True,
                'post_id': post_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to post. Make sure Instagram is connected.'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/integrations/usage')
@login_required
def get_usage_stats():
    """Get integration usage stats"""
    try:
        stats = integrations_manager.get_usage_stats(current_user.id)
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

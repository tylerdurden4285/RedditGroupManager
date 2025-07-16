import logging
import os
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request, Depends, APIRouter
from reddit_manager.utils import get_app_version
from fastapi.responses import HTMLResponse
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.exc import IntegrityError
import sqlite3 
from pydantic import BaseModel, Field, ConfigDict
import praw
from dotenv import load_dotenv
from reddit_manager.config.settings import Settings

from reddit_manager.services.reddit_service import RedditService
from reddit_manager.services.group_service import GroupService
from reddit_manager.services.user_service import UserService



load_dotenv()
settings = Settings()
reddit_service = RedditService(settings)
group_service = GroupService(settings)
user_service = UserService(settings)


logger = logging.getLogger(__name__)

# Application version loaded from package metadata with fallback
VERSION = get_app_version()

API_PREFIX = "/api/v1"


api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


def verify_token(api_key: str = Depends(api_key_header)):
    """Validate the Authorization token.

    The token is considered valid if it matches the global ``AUTH_KEY``
    environment variable or if it exists in the
    user database.
    """
    if not api_key:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

    
    env_key = os.getenv("AUTH_KEY")
    if env_key and api_key == env_key:
        return api_key

    
    user = user_service.get_user_by_api_key(api_key)
    if not user:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    return api_key


reddit_username = settings.reddit_username or "Not set"
app = FastAPI(
    title="Reddit API",
    description=f"RESTful API for Reddit operations and group management\nThis API is used by: **{reddit_username}**",
    version=VERSION,
    openapi_tags=[
        {
            "name": "groups",
            "description": "Group management operations",
        },
        {
            "name": "subreddits",
            "description": "Subreddit operations using PRAW",
        },
        {
            "name": "posts",
            "description": "Reddit post operations",
        },
        {
            "name": "auth",
            "description": "Authentication operations",
        }
    ],
)





class GroupBase(BaseModel):
    name: str
    description: str = ""

class GroupCreate(GroupBase):
    pass

class GroupUpdate(GroupBase):
    pass

class SubredditBase(BaseModel):
    subreddit: str
    flair_id: Optional[str] = None

class SubredditCreate(SubredditBase):
    pass

class SubredditUpdate(SubredditBase):
    pass

class PostBase(BaseModel):
    title: str
    flair_id: Optional[str] = None

class TextPostCreate(PostBase):
    body: str

class LinkPostCreate(PostBase):
    url: str

class CommentCreate(BaseModel):
    text: str





class GroupResponse(GroupBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class SubredditResponse(SubredditBase):
    id: int = None

    model_config = ConfigDict(from_attributes=True)

class GroupWithSubredditsResponse(GroupResponse):
    subreddits: List[SubredditResponse] = []

    model_config = ConfigDict(from_attributes=True)

class PostResponse(BaseModel):
    id: str
    url: str

    model_config = ConfigDict(from_attributes=True)

class CommentResponse(BaseModel):
    id: str
    url: str

    model_config = ConfigDict(from_attributes=True)

class AuthResponse(BaseModel):
    username: str
    authenticated: bool





@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    return """
    <html>
        <head>
            <link rel="stylesheet" href="https://unpkg.com/@picocss/pico@latest/css/pico.min.css">
            <title>Reddit API</title>
        </head>
        <body class="container" style="display: flex; justify-content: center; align-items: center; height: 100vh;">
            <div class="container">
                <article style="text-align: center;">
                    <h1>Reddit API</h1>
                    <p>RESTful API for Reddit operations and group management</p>
                    <p><a href="/docs">API Documentation</a></p>
                </article>
            </div>
        </body>
    </html>
    """

@app.get("/health", tags=["auth"])
def health_check():
    """Simple health check returning the API status and version."""
    return {"status": "healthy", "version": VERSION}





@app.get(f"{API_PREFIX}/auth/status", response_model=AuthResponse, tags=["auth"])
def auth_status(auth_key: str = Depends(verify_token)):
    try:
        username = reddit_service.get_reddit_username()
        logger.info(f"Auth check successful, Reddit username: {username}")
        return {"username": username, "authenticated": True}
    except Exception as e:
        logger.error(f"Error during auth check: {e}")
        raise HTTPException(status_code=500, detail=f"Error during auth check: {str(e)}")





@app.get(f"{API_PREFIX}/groups", response_model=List[GroupResponse], tags=["groups"])
def list_groups(auth_key: str = Depends(verify_token)):
    """Get all groups."""
    try:
        groups = group_service.list_groups()
        return groups
    except Exception as e:
        logger.error(f"Error listing groups: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing groups: {str(e)}")

@app.post(f"{API_PREFIX}/groups", response_model=GroupResponse, status_code=201, tags=["groups"])
def create_group(group: GroupCreate, auth_key: str = Depends(verify_token)):
    """Create a new group."""
    try:
        new_group_id = group_service.create_group(group.name, group.description)
        if new_group_id is None:
            
            
            logger.error(f"GroupService.create_group for '{group.name}' returned None without raising IntegrityError.")
            raise HTTPException(status_code=500, detail="Failed to create group due to an internal error.")
        
        created_group = group_service.get_group(new_group_id)
        if not created_group:
            logger.error(f"Group '{group.name}' (ID: {new_group_id}) created but could not be retrieved immediately.")
            raise HTTPException(status_code=500, detail="Group created but failed to retrieve for response.")

        logger.info(f"Group '{created_group.name}' created with ID: {created_group.id}")
        return created_group 
    except IntegrityError: 
        logger.warning(f"Failed to create group '{group.name}' because it already exists.")
        raise HTTPException(status_code=409, detail=f"Group with name '{group.name}' already exists.")
    except Exception as e:
        logger.error(f"Error creating group '{group.name}': {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get(f"{API_PREFIX}/groups/{{group_id}}", response_model=GroupWithSubredditsResponse, tags=["groups"])
def get_group(group_id: int, auth_key: str = Depends(verify_token)):
    """Get a specific group by ID."""
    try:
        group = group_service.get_group(group_id)
        if not group:
            logger.warning(f"Attempt to get non-existent group with ID: {group_id}")
            raise HTTPException(status_code=404, detail="Group not found")
        
        
        subreddits = group_service.get_group_subreddits(group_id)
        
        
        result = {**group.__dict__, "subreddits": subreddits}
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting group {group_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting group: {str(e)}")

@app.put(f"{API_PREFIX}/groups/{{group_id}}", response_model=GroupResponse, tags=["groups"])
def update_group(group_id: int, group: GroupUpdate, auth_key: str = Depends(verify_token)):
    """Update a group's details."""
    try:
        
        existing_group = group_service.get_group(group_id)
        if not existing_group:
            logger.warning(f"Attempt to update non-existent group with ID: {group_id}")
            raise HTTPException(status_code=404, detail="Group not found")

        success = group_service.update_group(group_id, group.name, group.description)
        if not success:
            
            
            logger.error(f"GroupService.update_group for ID {group_id} returned False.")
            raise HTTPException(status_code=500, detail="Failed to update group.")
        
        updated_group = group_service.get_group(group_id)
        if not updated_group:
            logger.error(f"Group {group_id} updated but could not be retrieved immediately.")
            raise HTTPException(status_code=500, detail="Group updated but failed to retrieve for response.")

        logger.info(f"Group {updated_group.id} updated to name '{updated_group.name}'.")
        return updated_group 
    except IntegrityError: 
        logger.warning(f"Failed to update group {group_id} to name '{group.name}' due to name conflict.")
        raise HTTPException(status_code=409, detail=f"A group with name '{group.name}' already exists.")
    except Exception as e:
        logger.error(f"Error updating group {group_id}: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.delete(f"{API_PREFIX}/groups/{{group_id}}", status_code=204, tags=["groups"])
def delete_group(group_id: int, auth_key: str = Depends(verify_token)):
    """Delete a group."""
    try:
        success = group_service.delete_group(group_id)
        if not success:
            raise HTTPException(status_code=404, detail="Group not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting group {group_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting group: {str(e)}")





@app.get(f"{API_PREFIX}/groups/{{group_id}}/subreddits", response_model=List[SubredditResponse], tags=["groups"])
def list_group_subreddits(group_id: int, auth_key: str = Depends(verify_token)):
    """Get all subreddits in a group."""
    try:
        if not group_service.get_group(group_id): 
            logger.warning(f"Attempt to list subreddits for non-existent group ID: {group_id}")
            raise HTTPException(status_code=404, detail=f"Group with id {group_id} not found")

        subreddits = group_service.get_group_subreddits(group_id)
        return subreddits
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing subreddits for group {group_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing subreddits: {str(e)}")

@app.post(f"{API_PREFIX}/groups/{{group_id}}/subreddits", response_model=SubredditResponse, status_code=201, tags=["groups"])
def add_subreddit_to_group(group_id: int, subreddit: SubredditCreate, auth_key: str = Depends(verify_token)):
    """Add a subreddit to a group."""
    try:
        
        if not group_service.get_group(group_id): 
            logger.warning(f"Attempt to add subreddit to non-existent group ID: {group_id}")
            raise HTTPException(status_code=404, detail=f"Group with id {group_id} not found")

        try:
            
            
            
            association_id = group_service.add_subreddit_to_group(
                group_id,
                subreddit.subreddit, 
                subreddit.flair_id   
            )
            if association_id is None:
                
                
                logger.error(f"Failed to add subreddit '{subreddit.subreddit}' to group {group_id}. group_service.add_subreddit_to_group returned None.")
                raise HTTPException(status_code=500, detail=f"Failed to add subreddit {subreddit.subreddit} to group {group_id}.")

            
            added_subreddit_obj = group_service.get_subreddit_by_name(subreddit.subreddit)
            if not added_subreddit_obj:
                logger.error(f"Subreddit '{subreddit.subreddit}' was reportedly added to group {group_id} (assoc_id: {association_id}), but could not be fetched by name.")
                raise HTTPException(status_code=500, detail="Subreddit added to group but could not be retrieved by name.")

            logger.info(f"Subreddit '{added_subreddit_obj.name}' (ID: {added_subreddit_obj.id}) associated with group {group_id} (Flair ID: {subreddit.flair_id}). Association ID: {association_id}.")
            
            
            
            
            return SubredditResponse(
                id=added_subreddit_obj.id, 
                subreddit=added_subreddit_obj.name, 
                flair_id=subreddit.flair_id 
            )
        except IntegrityError: 
            logger.warning(f"Subreddit '{subreddit.subreddit}' already exists in group {group_id}.")
            raise HTTPException(status_code=409, detail=f"Subreddit '{subreddit.subreddit}' already exists in group {group_id}.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding subreddit '{subreddit.subreddit}' to group {group_id}: {e}")
        
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.delete(f"{API_PREFIX}/groups/{{group_id}}/subreddits/{{subreddit_name}}", status_code=204, tags=["groups"])
def remove_subreddit_from_group(group_id: int, subreddit_name: str, auth_key: str = Depends(verify_token)):
    """Remove a subreddit from a group."""
    try:
        if not group_service.get_group(group_id): 
            logger.warning(f"Attempt to remove subreddit from non-existent group ID: {group_id}")
            raise HTTPException(status_code=404, detail=f"Group with id {group_id} not found")
        if not group_service.get_group(group_id):
            raise HTTPException(status_code=404, detail="Group not found")
        
        success = group_service.remove_subreddit_from_group(group_id, subreddit_name)
        if not success:
            raise HTTPException(status_code=404, detail="Subreddit not found in group")
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing subreddit from group {group_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error removing subreddit: {str(e)}")





@app.get(f"{API_PREFIX}/subreddits/{{subreddit_name}}", tags=["subreddits"])
def get_subreddit_info(subreddit_name: str, auth_key: str = Depends(verify_token)):
    """Get information about a subreddit."""
    try:
        info = reddit_service.get_subreddit_info(subreddit_name)
        logger.info(f"Fetched info for subreddit: {subreddit_name}")
        return {"subreddit": subreddit_name, "info": info}
    except praw.exceptions.PRAWException as e:
        logger.error(f"PRAW error fetching info for subreddit {subreddit_name}: {e}")
        raise HTTPException(status_code=400, detail=f"PRAW error fetching info: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching info for subreddit {subreddit_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching info: {str(e)}")

@app.get(f"{API_PREFIX}/subreddits/{{subreddit_name}}/flairs", tags=["subreddits"])
def get_subreddit_flairs(subreddit_name: str, auth_key: str = Depends(verify_token)):
    """Get available flairs for a subreddit."""
    try:
        flairs = reddit_service.get_subreddit_flairs(subreddit_name)
        logger.info(f"Fetched flairs for subreddit: {subreddit_name}")
        return {"subreddit": subreddit_name, "flairs": flairs}
    except praw.exceptions.PRAWException as e:
        logger.error(f"PRAW error fetching flairs for subreddit {subreddit_name}: {e}")
        raise HTTPException(status_code=400, detail=f"PRAW error fetching flairs: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching flairs for subreddit {subreddit_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching flairs: {str(e)}")

@app.post(f"{API_PREFIX}/subreddits/{{subreddit_name}}/posts", response_model=PostResponse, tags=["subreddits"])
def create_post(
    subreddit_name: str, 
    post: Dict[str, Any], 
    auth_key: str = Depends(verify_token)
):
    """Create a post in a subreddit.
    
    This endpoint accepts either a text post or a link post. The type is determined by
    the presence of either a 'body' field (text post) or a 'url' field (link post).
    """
    try:
        title = post.get("title")
        if not title:
            raise HTTPException(status_code=400, detail="Title is required")

        
        if "body" in post:
            body = post.get("body")
            post_type = "text"
            content = body
        elif "url" in post:
            url = post.get("url")
            post_type = "link"
            content = url
        else:
            raise HTTPException(status_code=400, detail="Either 'body' (text post) or 'url' (link post) is required")

        sub_flair = post.get("flair_id")
        post_data = {
            "subreddit": subreddit_name,
            "title": title,
            "content": content,
            "created_at": group_service.get_current_timestamp(),
            "post_type": post_type,
            "comment": post.get("comment"),
            "flair_id": sub_flair,
        }
        post_db_id = group_service.create_processing_post(post_data)
        app.queue.enqueue(process_post, post_db_id)
        return {"id": post_db_id}
    except HTTPException:
        raise
    except praw.exceptions.PRAWException as e:
        logger.error(f"PRAW error creating post in {subreddit_name}: {e}")
        raise HTTPException(status_code=400, detail=f"PRAW error creating post: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error creating post in {subreddit_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error creating post: {str(e)}")





@app.get(f"{API_PREFIX}/posts/{{post_id}}", tags=["posts"])
def get_post(post_id: str, auth_key: str = Depends(verify_token)):
    """Get information about a post."""
    try:
        
        
        return {"id": post_id, "url": f"https://reddit.com/{post_id}"}
    except Exception as e:
        logger.error(f"Error getting post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting post: {str(e)}")

@app.post(f"{API_PREFIX}/posts/{{post_id}}/comments", response_model=CommentResponse, tags=["posts"])
def create_comment(post_id: str, comment: CommentCreate, auth_key: str = Depends(verify_token)):
    """Add a comment to a post."""
    try:
        comment_id, comment_link = reddit_service.comment_on_post(post_id, comment.text)
        logger.info(f"Created comment on post {post_id}")
        return {"id": comment_id, "url": f"https://reddit.com{comment_link}"}
    except praw.exceptions.PRAWException as e:
        logger.error(f"PRAW error commenting on post {post_id}: {e}")
        raise HTTPException(status_code=400, detail=f"PRAW error commenting on post: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error commenting on post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error commenting on post: {str(e)}")





@app.post(f"{API_PREFIX}/comments/{{comment_id}}/replies", response_model=CommentResponse, tags=["posts"])
def create_reply(comment_id: str, reply: CommentCreate, auth_key: str = Depends(verify_token)):
    """Reply to a comment."""
    try:
        reply_id, reply_link = reddit_service.reply_to_comment(comment_id, reply.text)
        logger.info(f"Created reply to comment {comment_id}")
        return {"id": reply_id, "url": f"https://reddit.com{reply_link}"}
    except praw.exceptions.PRAWException as e:
        logger.error(f"PRAW error replying to comment {comment_id}: {e}")
        raise HTTPException(status_code=400, detail=f"PRAW error replying to comment: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error replying to comment {comment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error replying to comment: {str(e)}")





@app.post(f"{API_PREFIX}/groups/{{group_id}}/posts", tags=["groups", "posts"])
def create_post_in_group(
    group_id: int, 
    post: Dict[str, Any], 
    auth_key: str = Depends(verify_token)
):
    """Create a post in all subreddits of a group.
    
    This endpoint accepts either a text post or a link post. The type is determined by
    the presence of either a 'body' field (text post) or a 'url' field (link post).
    """
    try:
        
        group = group_service.get_group(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
            
        
        subreddits = group_service.get_group_subreddits(group_id)
        if not subreddits:
            raise HTTPException(status_code=404, detail="No subreddits found in this group")
            
        title = post.get("title")
        if not title:
            raise HTTPException(status_code=400, detail="Title is required")
            
        
        is_text_post = "body" in post
        is_link_post = "url" in post
        
        if not (is_text_post or is_link_post):
            raise HTTPException(status_code=400, detail="Either 'body' (text post) or 'url' (link post) is required")
            
        results = []
        for subreddit_obj in subreddits:
            subreddit_name = getattr(subreddit_obj, "name", None) or getattr(subreddit_obj, "subreddit", None)
            flair_id = getattr(subreddit_obj, "flair_id", None)

            try:
                if is_text_post:
                    body = post.get("body")
                    post_id = reddit_service.post_to_subreddit(subreddit_name, title, body, flair_id)
                else:  
                    url = post.get("url")
                    post_id = reddit_service.post_link_to_subreddit(subreddit_name, title, url, flair_id)

                results.append({
                    "subreddit": subreddit_name,
                    "post_id": post_id,
                    "post_url": f"https://www.reddit.com/r/{subreddit_name}/comments/{post_id}",
                    "success": True
                })
            except Exception as e:
                results.append({
                    "subreddit": subreddit_name,
                    "error": str(e),
                    "success": False
                })

        return {
            "group_id": group_id,
            "group_name": group.name,
            "results": results
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error posting to group {group_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error posting to group: {str(e)}")











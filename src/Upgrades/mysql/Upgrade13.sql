ALTER TABLE favoritee ADD COLUMN fav_date INTEGER DEFAULT NULL;
ALTER TABLE post ADD COLUMN fav_date INTEGER DEFAULT NULL;

DROP TRIGGER favoritee_update;

CREATE TRIGGER favoritee_update AFTER UPDATE ON favoritee FOR EACH ROW
BEGIN
	UPDATE post SET fav_count = fav_count + 1 WHERE post.id = new.post_id;
	UPDATE post SET fav_count = fav_count - 1 WHERE post.id = old.post_id;
	UPDATE post SET fav_date = (SELECT MAX(fav_date) FROM favoritee WHERE favoritee.post_id = post.id);
END;

DROP TRIGGER favoritee_insert;

CREATE TRIGGER favoritee_insert AFTER INSERT ON favoritee FOR EACH ROW
BEGIN
	UPDATE post SET fav_count = fav_count + 1 WHERE post.id = new.post_id;
	UPDATE post SET fav_date = (SELECT MAX(fav_date) FROM favoritee WHERE favoritee.post_id = post.id);
END;

DROP TRIGGER favoritee_delete;

CREATE TRIGGER favoritee_delete AFTER DELETE ON favoritee FOR EACH ROW
BEGIN
	UPDATE post SET fav_count = fav_count - 1 WHERE post.id = old.post_id;
	UPDATE post SET fav_date = (SELECT MAX(fav_date) FROM favoritee WHERE favoritee.post_id = post.id);
END;
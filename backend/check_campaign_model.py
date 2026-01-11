from app.models.models import Campaign

print('Campaign columns:')
for c in Campaign.__table__.columns:
    print('-', c.name, str(c.type))

print('has customer_info attr:', hasattr(Campaign, 'customer_info'))

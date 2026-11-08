import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'site'))
from product_campaigns import select_products, media_id, campaign


class ProductCampaignTests(unittest.TestCase):
    def setUp(self):
        self.product={'asin':'B0ZZZZZZZZ','added':'2026-11-07','sitestripe_url':'https://www.amazon.com/dp/B0ZZZZZZZZ?tag=test-20',
            'photo_review':{'exact_product':True,'sha256':'fixture'},'graphic':{'points':['One','Two','Three']},'suits':'Fit','check':'Check size',
            'page_url':'https://kitchenfindsfavorites.com/picks/fixture/','pin_image':'https://kitchenfindsfavorites.com/img/fixture.png',
            'pin':{'title':'Fixture','description':'#ad Fixture','board':'Fixture'}}

    def test_excludes_legacy_and_other_release_dates(self):
        legacy=dict(self.product);legacy.pop('photo_review')
        eligible,today=select_products([legacy,dict(self.product,added='2026-11-06')],'2026-11-07')
        self.assertEqual(len(eligible),1)
        self.assertEqual(today,[])

    def test_duplicate_and_sixteenth_product_fail(self):
        with self.assertRaises(ValueError):select_products([self.product,self.product],'2026-11-07')
        with self.assertRaises(ValueError):select_products([dict(self.product,asin=str(i)) for i in range(16)],'2026-11-07')

    def test_assets_change_identity_and_no_false_post_success(self):
        changed=copy.deepcopy(self.product);changed['photo_review']['sha256']='changed'
        self.assertNotEqual(media_id(self.product),media_id(changed))
        item=campaign(self.product,'https://kitchenfindsfavorites.com')
        self.assertEqual(len(item['platforms']),5)
        for platform,post in item['platforms'].items():
            self.assertIsNone(post['post_url'])
            self.assertEqual(post['status'],'awaiting_native_duplicate_check_and_publish')
            self.assertIn('utm_source='+platform,post['website_link'])


if __name__=='__main__':unittest.main()

import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    {
        path: '/',
        name: 'home',
        component: () => import('@/views/HomeView.vue'),
    },
    {
        path: '/viewpoint/:id',
        name: 'viewpoint-detail',
        component: () => import('@/views/ViewpointDetail.vue'),
        props: true,
    },
    {
        path: '/viewpoint/:id/:date',
        name: 'viewpoint-date',
        component: () => import('@/views/ViewpointDetail.vue'),
        props: true,
    },
    {
        path: '/route/:id',
        name: 'route-detail',
        component: () => import('@/views/RouteDetail.vue'),
        props: true,
    },
    {
        path: '/ops/poster',
        name: 'poster',
        component: () => import('@/views/PosterView.vue'),
    },
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

export default router
